from __future__ import annotations

import math
from io import BytesIO

import pandas as pd

from app.errors import AppError

LAT_KEYWORDS = ("lat", "latitud", "latitude", "coordenada_y", "y")
LON_KEYWORDS = ("lon", "lng", "long", "longitud", "longitude", "coordenada_x", "x")


def read_uploaded_table(filename: str, content: bytes) -> pd.DataFrame:
    lowered_name = filename.lower()
    if lowered_name.endswith(".csv"):
        try:
            return pd.read_csv(BytesIO(content), sep=None, engine="python", encoding_errors="replace")
        except Exception as exc:
            raise AppError(f"No se pudo leer el CSV: {exc}") from exc
    if lowered_name.endswith(".xlsx"):
        try:
            return pd.read_excel(BytesIO(content), engine="openpyxl")
        except Exception as exc:
            raise AppError(f"No se pudo leer el archivo Excel: {exc}") from exc
    raise AppError("Formato no soportado. Usa archivos .csv o .xlsx.")


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    sanitized = df.copy()
    sanitized.columns = [str(col).strip() or f"Columna_{index + 1}" for index, col in enumerate(sanitized.columns)]
    sanitized = sanitized.fillna("")
    return sanitized


def _normalize_header(column_name: str) -> str:
    return str(column_name).strip().lower().replace(" ", "_")


def _looks_like_coordinate_header(column_name: str) -> bool:
    normalized = _normalize_header(column_name)
    return any(keyword in normalized for keyword in (*LAT_KEYWORDS, *LON_KEYWORDS))


def _coerce_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")


def _score_column(series: pd.Series, column_name: str, keywords: tuple[str, ...], valid_range: tuple[float, float]) -> float:
    normalized_header = _normalize_header(column_name)
    header_score = 0.0
    if normalized_header in keywords:
        header_score += 4.0
    elif any(keyword in normalized_header for keyword in keywords):
        header_score += 2.0

    numeric_series = _coerce_numeric_series(series)
    non_null = numeric_series.dropna()
    if non_null.empty:
        return header_score

    range_score = ((non_null >= valid_range[0]) & (non_null <= valid_range[1])).mean() * 4.0
    variability_score = 1.0 if non_null.nunique() > 4 else 0.0
    return header_score + range_score + variability_score


def detect_coordinate_columns(df: pd.DataFrame) -> tuple[str | None, str | None, list[str]]:
    notes: list[str] = []
    lat_scores = {column: _score_column(df[column], column, LAT_KEYWORDS, (-90, 90)) for column in df.columns}
    lon_scores = {column: _score_column(df[column], column, LON_KEYWORDS, (-180, 180)) for column in df.columns}

    ordered_lat = sorted(lat_scores.items(), key=lambda item: item[1], reverse=True)
    ordered_lon = sorted(lon_scores.items(), key=lambda item: item[1], reverse=True)

    lat_column = ordered_lat[0][0] if ordered_lat and ordered_lat[0][1] >= 3 else None
    lon_column = ordered_lon[0][0] if ordered_lon and ordered_lon[0][1] >= 3 else None

    if lat_column and lon_column and lat_column == lon_column:
        lon_column = ordered_lon[1][0] if len(ordered_lon) > 1 and ordered_lon[1][1] >= 3 else None

    if not lat_column or not lon_column:
        notes.append("No se pudo detectar con seguridad la pareja latitud/longitud. El alumno debe confirmarla manualmente.")
    else:
        notes.append(f"Columnas sugeridas: latitud `{lat_column}` y longitud `{lon_column}`.")

    return lat_column, lon_column, notes


def suggest_category_columns(df: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for column in df.columns:
        if _looks_like_coordinate_header(column):
            continue
        unique_values = df[column].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        if 1 < unique_values <= 12:
            candidates.append(column)
    return candidates[:8]


def suggest_label_columns(df: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for column in df.columns:
        if _looks_like_coordinate_header(column):
            continue
        non_empty = df[column].astype(str).str.strip().replace("", pd.NA).dropna()
        if not non_empty.empty and non_empty.str.len().median() <= 40:
            candidates.append(column)
    return candidates[:8]


def preview_rows(df: pd.DataFrame, limit: int = 8) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in df.head(limit).to_dict(orient="records"):
        rows.append({key: "" if value is None else str(value) for key, value in row.items()})
    return rows


def _within_range(value: float, minimum: float, maximum: float) -> bool:
    return not math.isnan(value) and minimum <= value <= maximum


def validate_coordinates(df: pd.DataFrame, lat_column: str, lon_column: str) -> tuple[pd.DataFrame, dict]:
    if lat_column not in df.columns or lon_column not in df.columns:
        raise AppError("Las columnas seleccionadas no existen en el archivo.")

    working = df.copy()
    working["__lat"] = _coerce_numeric_series(working[lat_column])
    working["__lon"] = _coerce_numeric_series(working[lon_column])

    total_rows = len(working)
    invalid_breakdown: list[str] = []

    non_numeric_lat = int(working["__lat"].isna().sum())
    non_numeric_lon = int(working["__lon"].isna().sum())
    if non_numeric_lat:
        invalid_breakdown.append(f"{non_numeric_lat} filas sin latitud numerica valida.")
    if non_numeric_lon:
        invalid_breakdown.append(f"{non_numeric_lon} filas sin longitud numerica valida.")

    range_mask = working["__lat"].between(-90, 90) & working["__lon"].between(-180, 180)
    swapped_mask = working["__lat"].between(-180, 180) & working["__lon"].between(-90, 90)
    out_of_range = (~working["__lat"].isna() & ~working["__lon"].isna() & ~range_mask).sum()
    if out_of_range:
        invalid_breakdown.append(f"{int(out_of_range)} filas quedaron fuera de rango geografico.")

    detected_swap_warning = bool(swapped_mask.mean() > 0.5 and not range_mask.mean() > 0.5)
    if detected_swap_warning:
        invalid_breakdown.append("Se detecto un posible intercambio entre latitud y longitud.")

    cleaned = working.loc[range_mask].copy()
    cleaned.rename(columns={lat_column: "latitud_original", lon_column: "longitud_original"}, inplace=True)
    cleaned["lat"] = cleaned["__lat"]
    cleaned["lon"] = cleaned["__lon"]
    cleaned.drop(columns=["__lat", "__lon"], inplace=True)

    bounds = None
    if not cleaned.empty:
        bounds = {
            "south": float(cleaned["lat"].min()),
            "north": float(cleaned["lat"].max()),
            "west": float(cleaned["lon"].min()),
            "east": float(cleaned["lon"].max()),
        }

    summary = {
        "total_rows": total_rows,
        "valid_rows": int(len(cleaned)),
        "invalid_rows": int(total_rows - len(cleaned)),
        "invalid_breakdown": invalid_breakdown,
        "bounds": bounds,
        "detected_swap_warning": detected_swap_warning,
    }
    return cleaned, summary


def build_points_payload(df: pd.DataFrame, lat_column: str, lon_column: str, label_column: str | None, category_column: str | None) -> tuple[list[dict], list[str]]:
    if label_column and label_column not in df.columns:
        raise AppError("La columna elegida para etiqueta no existe en la sesion cargada.")
    if category_column and category_column not in df.columns:
        raise AppError("La columna elegida para categoria no existe en la sesion cargada.")

    popup_fields = [column for column in df.columns if column not in {"lat", "lon", lat_column, lon_column, "latitud_original", "longitud_original"}]
    popup_fields = popup_fields[:6]

    points: list[dict] = []
    for _, row in df.iterrows():
        popup = {field: str(row[field]) for field in popup_fields if str(row[field]).strip()}
        label = str(row[label_column]).strip() if label_column and label_column in df.columns else ""
        category = str(row[category_column]).strip() if category_column and category_column in df.columns else "Sin categoria"
        points.append(
            {
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "label": label,
                "category": category,
                "popup": popup,
            }
        )
    return points, popup_fields
