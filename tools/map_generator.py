import folium
import pandas as pd
from folium.plugins import Fullscreen, HeatMap

HEATMAP_PALETTES = {
    'Classic': None, 'Viridis': [[0.0, '#440154'], [0.25, '#3b528b'], [0.5, '#21908d'], [0.75, '#5dc863'], [1.0, '#fde725']],
    'Inferno': [[0.0, '#000004'], [0.25, '#500064'], [0.5, '#bb3754'], [0.75, '#fca434'], [1.0, '#fcffa4']],
    'Plasma': [[0.0, '#0d0887'], [0.25, '#7e03a8'], [0.5, '#cb4778'], [0.75, '#f89540'], [1.0, '#f0f921']],
    'Turbo': [[0.0, '#23171b'], [0.25, '#489f65'], [0.5, '#95d143'], [0.75, '#fed953'], [1.0, '#e54b17']],
}
MAP_TILES = {
    'OpenStreetMap': ('OpenStreetMap', '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'),
    'CartoDB Positron': ('CartoDB positron', '&copy; <a href="https://carto.com/attributions">CARTO</a>'),
    'CartoDB DarkMatter': ('CartoDB dark_matter', '&copy; <a href="https://carto.com/attributions">CARTO</a>'),
    'Esri World Imagery': ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 'Tiles &copy; Esri'),
    'Esri WorldStreetMap': ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', 'Tiles &copy; Esri'),
}

def create_heatmap_overlay(df, params):
    """
    Función dedicada y especializada.
    Crea un mapa que contiene ÚNICAMENTE la capa de heatmap sobre un fondo transparente.
    No hay mapa base. No hay controles. Solo los datos.
    """
    bounds = [[df['_lat'].min(), df['_lon'].min()], [df['_lat'].max(), df['_lon'].max()]]
    
    # 1. Crear mapa con fondo explícitamente transparente
    m = folium.Map(tiles=None, prefer_canvas=True, bg_color='transparent')
    m.get_root().width = "100%"
    m.get_root().height = "100%"

    # 2. Añadir ÚNICAMENTE el heatmap
    add_heatmap_layer(m, df, params)

    # 3. Ajustar el zoom
    m.fit_bounds(bounds, padding=(50, 50))
    
    # 4. Inyectar CSS para asegurar que todo sea transparente
    style_fix = "<style>body, .leaflet-container { background-color: transparent !important; }</style>"
    m.get_root().html.add_child(folium.Element(style_fix))
    return m


def create_map(df, params, geo_cols, is_for_export=False):
    """
    Crea un mapa para visualización o para exportaciones que SÍ necesitan un mapa de fondo (PDF).
    """
    m = folium.Map(tiles=None, prefer_canvas=True, control_scale=True, zoom_control=not is_for_export)
    m.get_root().width = "100%"
    m.get_root().height = "100%"

    # Añadir siempre un mapa base
    selected_tile_name = params.get('tile_layer', 'OpenStreetMap')
    base_tile_url, base_tile_attr = MAP_TILES.get(selected_tile_name, MAP_TILES['OpenStreetMap'])
    folium.TileLayer(tiles=base_tile_url, attr=base_tile_attr, name=selected_tile_name).add_to(m)

    # Añadir datos
    map_type = params.get('map_type', 'points')
    layer_name = 'Mapa de Calor' if map_type == 'heatmap' else 'Puntos Individuales'
    feature_group = folium.FeatureGroup(name=layer_name, show=True)
    m.add_child(feature_group)

    if map_type == 'points':
        add_points_layer(feature_group, df, geo_cols)
    elif map_type == 'heatmap':
        add_heatmap_layer(feature_group, df, params)

    bounds = [[df['_lat'].min(), df['_lon'].min()], [df['_lat'].max(), df['_lon'].max()]]
    m.fit_bounds(bounds, padding=(50, 50))

    # Añadir controles de interfaz solo si no es para exportar
    if not is_for_export:
        for name, (url, attr) in MAP_TILES.items():
            if name != selected_tile_name:
                folium.TileLayer(tiles=url, attr=attr, name=name).add_to(m)
        Fullscreen(position="topleft", title="Pantalla Completa").add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
    
    map_id = m.get_name()
    js_fix = f"<script>setTimeout(function() {{ try {{ window.dispatchEvent(new Event('resize')); {map_id}.invalidateSize(); }} catch(e) {{}} }}, 500);</script>"
    m.get_root().html.add_child(folium.Element(js_fix))

    return m

def add_points_layer(parent_layer, df, geo_cols):
    popup_cols = [col for col in df.columns if col not in ['_lat', '_lon'] and col not in geo_cols.values()][:6]
    for _, row in df.iterrows():
        popup_html = ""
        for col in popup_cols:
            if pd.notna(row[col]):
                popup_html += f"<b>{col}:</b> {row[col]}<br>"
        div_icon = folium.DivIcon(
            class_name='custom-div-icon',
            html=f'<div class="fa fa-bullseye" style="font-size: 16px; color: white; background-color: red; border-radius: 50%; width: 24px; height: 24px; text-align: center; line-height: 24px;"></div>'
        )
        folium.Marker(location=[row['_lat'], row['_lon']], popup=folium.Popup(popup_html, max_width=300), icon=div_icon).add_to(parent_layer)

def add_heatmap_layer(parent_layer, df, params):
    radius = int(params.get('radius', 25))
    palette_name = params.get('palette', 'Classic')
    gradient = HEATMAP_PALETTES.get(palette_name)
    heat_data = df[['_lat', '_lon']].values.tolist()
    HeatMap(heat_data, radius=radius, gradient=gradient).add_to(parent_layer)