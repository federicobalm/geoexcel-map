import pandas as pd

POSSIBLE_LAT_COLS = ['lat', 'latitude', 'latitud', 'y']
POSSIBLE_LON_COLS = ['lon', 'lng', 'long', 'longitude', 'longitud', 'x']

def find_geo_columns(df):
    cols = [str(c).lower().strip() for c in df.columns]
    lat_found = [df.columns[i] for i, c in enumerate(cols) if c in POSSIBLE_LAT_COLS]
    lon_found = [df.columns[i] for i, c in enumerate(cols) if c in POSSIBLE_LON_COLS]
    return lat_found, lon_found

def process_excel(filepath, selected_cols=None):
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
        
        if selected_cols:
            # --- LÓGICA MEJORADA PARA PROCESAR COORDENADAS ---
            lat_col_name = selected_cols['lat']
            lon_col_name = selected_cols['lon']

            # 1. Asegurarse de que las columnas son de tipo string para poder manipularlas.
            df[lat_col_name] = df[lat_col_name].astype(str)
            df[lon_col_name] = df[lon_col_name].astype(str)

            # 2. Reemplazar comas por puntos para estandarizar el separador decimal.
            df[lat_col_name] = df[lat_col_name].str.replace(',', '.', regex=False)
            df[lon_col_name] = df[lon_col_name].str.replace(',', '.', regex=False)
            
            # 3. Renombrar y convertir a número. 'coerce' convierte los errores en 'NaN' (Not a Number).
            df.rename(columns={lat_col_name: '_lat', lon_col_name: '_lon'}, inplace=True)
            df['_lat'] = pd.to_numeric(df['_lat'], errors='coerce')
            df['_lon'] = pd.to_numeric(df['_lon'], errors='coerce')

            # 4. Eliminar cualquier fila donde la conversión falló.
            df.dropna(subset=['_lat', '_lon'], inplace=True)
            return df

        # La lógica de detección de columnas se mantiene igual
        lat_cols, lon_cols = find_geo_columns(df)
        if not lat_cols or not lon_cols:
            return {'error': 'No se encontraron columnas de latitud/longitud.'}
        if len(lat_cols) > 1 or len(lon_cols) > 1:
            return {'ambiguous': True, 'lat_options': lat_cols, 'lon_options': lon_cols}
        
        return {'ambiguous': False, 'columns': {'lat': lat_cols[0], 'lon': lon_cols[0]}}

    except Exception as e:
        return {'error': f'Error al leer el archivo Excel: {str(e)}'}