"""Cartographic descriptions and metric Gaussian KDE for synthetic teaching data."""
from datetime import datetime, timezone

import numpy as np
from pyproj import Transformer

from app.errors import AppError


def gaussian_density(df, bandwidth):
    if df.empty:
        raise AppError('La KDE requiere al menos un evento con coordenadas validas.')
    lat = df['lat'].to_numpy(dtype=float)
    lon = df['lon'].to_numpy(dtype=float)
    if lat.min() < -80 or lat.max() > 84:
        raise AppError('La KDE local utiliza UTM y admite latitudes entre 80 grados sur y 84 grados norte.')
    zone = min(60, int((lon.mean() + 180) // 6) + 1)
    epsg = (32600 if lat.mean() >= 0 else 32700) + zone
    forward = Transformer.from_crs(4326, epsg, always_xy=True)
    inverse = Transformer.from_crs(epsg, 4326, always_xy=True)
    x, y = forward.transform(lon, lat)
    if np.ptp(x) > 300000 or np.ptp(y) > 300000:
        raise AppError('La KDE local admite una extension de hasta 300 km por eje. Dividi el estudio en unidades locales.')
    if max(np.ptp(x), np.ptp(y)) / 96 > bandwidth / 2:
        raise AppError('El ancho de banda es demasiado pequeno para la extension y resolucion de esta KDE. Aumentalo o reduci el area de estudio.')
    padding = 3 * bandwidth
    left, bottom = inverse.transform(float(x.min() - padding), float(y.min() - padding))
    right, top = inverse.transform(float(x.max() + padding), float(y.max() + padding))
    rows = cols = 96
    lons, lats = np.meshgrid(np.linspace(left, right, cols), np.linspace(top, bottom, rows))
    gx, gy = forward.transform(lons, lats)
    # Bin coincident/nearby events first; bounded work even for large uploads.
    counts, xe, ye = np.histogram2d(x, y, bins=96)
    density = np.zeros((rows, cols))
    for ix, iy in zip(*np.nonzero(counts)):
        cx, cy = (xe[ix] + xe[ix + 1]) / 2, (ye[iy] + ye[iy + 1]) / 2
        density += counts[ix, iy] * np.exp(-((gx - cx) ** 2 + (gy - cy) ** 2) / (2 * bandwidth ** 2))
    density *= 1e6 / (2 * np.pi * bandwidth ** 2)
    return {'rows': rows, 'cols': cols, 'values': density.ravel().tolist(),
            'bounds': [[bottom, left], [top, right]], 'maximum': float(density.max()),
            'bandwidth_m': bandwidth, 'epsg': epsg, 'units': 'eventos/km²',
            'method': 'KDE gaussiana aproximada por binning espacial (96 × 96); sin correccion de borde'}


def build_cartography(request, summary, df, density=None):
    meta = request.cartographic_metadata
    methods = {
        'points': 'Simbolos puntuales de tamano uniforme; sin clasificacion numerica.',
        'category': 'Clasificacion nominal por categoria; colores sin orden de magnitud.',
        'cluster': 'Agrupacion interactiva por proximidad en pantalla; el numero indica eventos, no una tasa.',
        'proportional': 'Frecuencia por coordenada coincidente; area del circulo proporcional al conteo, sin clases.',
        'heatmap': 'KDE gaussiana en UTM; escala secuencial continua con nodos de color manuales, no cuantiles ni Jenks.',
        'hotmap': 'Mapa de calor clasico: acumulacion suavizada de eventos en pantalla; intensidad relativa dependiente del zoom.',
        'choropleth': 'Coropleta por grilla: conteo de eventos en celdas de 7 × 7; cinco clases por fracciones del maximo (20%, 40%, 60%, 80%).',
        'profile': 'CGT/Rossmo: puntaje relativo de prioridad, no densidad ni probabilidad calibrada.'}
    total = summary.total_rows
    warnings = []
    duplicate_count = int(df.duplicated(subset=['lat', 'lon'], keep=False).sum())
    if duplicate_count:
        warnings.append(f'{duplicate_count} registros comparten coordenadas. Revisar centroides, alturas imputadas y duplicados antes de interpretar concentraciones.')
    warnings.append('El periodo fue declarado y confirmado por el analista; no se verificaron fechas individuales ni precision de direcciones.')
    return {
        'title': f'{meta.event} · {meta.geographic_unit} · {meta.period_start} a {meta.period_end}',
        'author': meta.author, 'created_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'basemap': request.tile_layer, 'method': methods[request.map_type],
        'geocoding_percentage': round(100 * summary.valid_rows / total, 2) if total else 0,
        'geocoding_description': f'{summary.valid_rows}/{total} registros con coordenadas validas. Cobertura de geoposicionamiento; no acredita geocodificacion de direcciones ni exactitud posicional.',
        'synthetic': True, 'warnings': warnings,
        'limitation': 'Concentracion y correlacion espacial no implican causalidad. Aplicar un proceso hipotetico-deductivo: contrastar hipotesis con evidencia independiente y teorias de Actividades Rutinarias y Patron Delictivo. La agregacion no garantiza por si sola anonimato ni cumplimiento de la Ley 25.326.',
    }
