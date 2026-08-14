from __future__ import annotations

import math

import numpy as np
from pyproj import Transformer

from app.models import GeographicProfile, MapRequest

EPSILON = 1e-6
GRID_SIZE = 200


def _infer_utm_epsg(lat: float, lon: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def _build_transformers(latitudes: np.ndarray, longitudes: np.ndarray) -> tuple[int, Transformer, Transformer]:
    epsg = _infer_utm_epsg(float(latitudes.mean()), float(longitudes.mean()))
    forward = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    inverse = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    return epsg, forward, inverse


def _distance(grid_x: np.ndarray, grid_y: np.ndarray, point_x: float, point_y: float, metric: str) -> np.ndarray:
    if metric == "euclidean":
        return np.sqrt((grid_x - point_x) ** 2 + (grid_y - point_y) ** 2)
    return np.abs(grid_x - point_x) + np.abs(grid_y - point_y)


def _nearest_grid_score(scores: np.ndarray, x_axis: np.ndarray, y_axis: np.ndarray, x: float, y: float) -> float:
    x_index = int(np.abs(x_axis - x).argmin())
    y_index = int(np.abs(y_axis - y).argmin())
    return float(scores[y_index, x_index])


def build_geographic_profile(df, map_request: MapRequest) -> GeographicProfile:
    latitudes = df["lat"].to_numpy(dtype=float)
    longitudes = df["lon"].to_numpy(dtype=float)
    crimes_used = int(len(df))

    epsg, forward, inverse = _build_transformers(latitudes, longitudes)
    crime_x, crime_y = forward.transform(longitudes, latitudes)
    crime_x = np.asarray(crime_x, dtype=float)
    crime_y = np.asarray(crime_y, dtype=float)

    buffer_radius = float(map_request.buffer_radius_m)
    span_x = float(crime_x.max() - crime_x.min()) if crimes_used > 1 else buffer_radius * 2
    span_y = float(crime_y.max() - crime_y.min()) if crimes_used > 1 else buffer_radius * 2
    dominant_span = max(span_x, span_y, buffer_radius * 2)
    padding = max(buffer_radius * 1.25, dominant_span * 0.15, 250.0)

    x_axis = np.linspace(float(crime_x.min() - padding), float(crime_x.max() + padding), GRID_SIZE)
    y_axis = np.linspace(float(crime_y.min() - padding), float(crime_y.max() + padding), GRID_SIZE)
    grid_x, grid_y = np.meshgrid(x_axis, y_axis)
    scores = np.zeros_like(grid_x, dtype=float)

    for point_x, point_y in zip(crime_x, crime_y):
        distance = _distance(grid_x, grid_y, float(point_x), float(point_y), map_request.distance_metric)
        outside_buffer = (distance > buffer_radius).astype(float)
        outside_denominator = np.maximum(distance, EPSILON)
        inside_denominator = np.maximum(2 * buffer_radius - distance, EPSILON)

        scores += map_request.scale_constant * (
            outside_buffer / np.power(outside_denominator, map_request.decay_exponent_out)
            + (1.0 - outside_buffer)
            * np.power(buffer_radius, map_request.decay_exponent_in - map_request.decay_exponent_out)
            / np.power(inside_denominator, map_request.decay_exponent_in)
        )

    score_min = float(scores.min())
    score_max = float(scores.max())
    if math.isclose(score_min, score_max):
        normalized = np.ones_like(scores, dtype=float)
    else:
        normalized = (scores - score_min) / (score_max - score_min)

    percentile_cutoff = 0.72 if crimes_used >= 5 else 0.82
    cutoff = max(float(np.quantile(normalized, percentile_cutoff)), 0.15)
    jeopardy_mask = normalized >= cutoff

    jeopardy_x = grid_x[jeopardy_mask]
    jeopardy_y = grid_y[jeopardy_mask]
    jeopardy_intensity = normalized[jeopardy_mask]
    jeopardy_lon, jeopardy_lat = inverse.transform(jeopardy_x, jeopardy_y)
    jeopardy_points = [
        [float(lat), float(lon), float(intensity)]
        for lat, lon, intensity in zip(jeopardy_lat.tolist(), jeopardy_lon.tolist(), jeopardy_intensity.tolist())
    ]

    anchor_index = np.unravel_index(int(scores.argmax()), scores.shape)
    anchor_x = float(grid_x[anchor_index])
    anchor_y = float(grid_y[anchor_index])
    anchor_lon, anchor_lat = inverse.transform(anchor_x, anchor_y)

    hit_score_percentage = None
    if map_request.known_anchor_lat is not None and map_request.known_anchor_lon is not None:
        known_x, known_y = forward.transform(map_request.known_anchor_lon, map_request.known_anchor_lat)
        anchor_score = _nearest_grid_score(scores, x_axis, y_axis, float(known_x), float(known_y))
        hit_score_percentage = float(((scores >= anchor_score).sum() / scores.size) * 100)

    warnings: list[str] = []
    notes = [
        "El pico probabilistico representa el centro mas probable de la base operativa, no la ubicacion del proximo ataque.",
        "El modelo aplica proyeccion UTM antes del calculo para evitar errores metricos sobre grados decimales.",
    ]

    if crimes_used < 5:
        warnings.append("La serie tiene menos de 5 delitos vinculados. El perfil puede ser inestable y sensible al sesgo de dispersion.")

    if map_request.distance_metric == "manhattan":
        notes.append("Se uso distancia Manhattan para aproximar desplazamientos en reticula urbana.")
        if not 300 <= map_request.buffer_radius_m <= 500:
            warnings.append("En entornos urbanos densos suele recomendarse un buffer entre 300 m y 500 m para mantener especificidad.")
    else:
        notes.append("Se uso distancia euclidiana para aproximar desplazamientos en entornos rurales o menos estructurados.")
        if not 1000 <= map_request.buffer_radius_m <= 1500:
            warnings.append("En entornos rurales suele recomendarse un buffer entre 1000 m y 1500 m para compensar la menor densidad de objetivos.")

    if map_request.buffer_radius_m > 1200 and map_request.distance_metric == "manhattan":
        warnings.append("Un buffer amplio eleva la probabilidad agregada pero reduce la especificidad espacial del perfil.")
    if map_request.buffer_radius_m < 250:
        warnings.append("Un buffer muy ajustado aumenta la precision potencial, pero tambien la sensibilidad a errores o outliers en la serie.")

    if hit_score_percentage is None:
        notes.append("El HS% solo puede calcularse si el analista informa un punto de anclaje conocido para evaluacion retrospectiva.")

    cell_size_x = abs(float(x_axis[1] - x_axis[0])) if len(x_axis) > 1 else 0.0
    cell_size_y = abs(float(y_axis[1] - y_axis[0])) if len(y_axis) > 1 else 0.0

    return GeographicProfile(
        crimes_used=crimes_used,
        grid_rows=GRID_SIZE,
        grid_cols=GRID_SIZE,
        projection_epsg=epsg,
        distance_metric=map_request.distance_metric,
        buffer_radius_m=map_request.buffer_radius_m,
        decay_exponent_out=map_request.decay_exponent_out,
        decay_exponent_in=map_request.decay_exponent_in,
        scale_constant=map_request.scale_constant,
        cell_size_m=float((cell_size_x + cell_size_y) / 2),
        hit_score_percentage=hit_score_percentage,
        anchor_estimate={"lat": float(anchor_lat), "lon": float(anchor_lon), "score": score_max},
        warnings=warnings,
        notes=notes,
        jeopardy_points=jeopardy_points,
    )
