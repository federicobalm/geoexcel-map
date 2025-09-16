import pandas as pd
import os

POSSIBLE_LAT_COLS = ['lat', 'latitud', 'latitude', 'y']
POSSIBLE_LON_COLS = ['lon', 'long', 'longitud', 'longitude', 'lng', 'x']

def read_data_file(filepath):
    """
    Lee de forma inteligente un archivo de datos, soportando múltiples formatos y detectando separadores.
    """
    _, extension = os.path.splitext(filepath)
    ext = extension.lower()

    try:
        if ext in ['.xlsx', '.xls']:
            return pd.read_excel(filepath, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
        elif ext in ['.csv', '.txt']:
            return pd.read_csv(filepath, sep=None, engine='python', encoding_errors='replace')
        else:
            return {'error': f"Formato de archivo no soportado: {ext}"}
    except Exception as e:
        return {'error': f"Error al leer el archivo: {e}"}

def analyze_columns(df):
    """
    Analiza las columnas de un DataFrame para encontrar candidatas a lat/lon.
    """
    cols = {str(c).lower().strip(): str(c) for c in df.columns}
    
    lat_found = [original_name for lower_name, original_name in cols.items() if any(key in lower_name for key in POSSIBLE_LAT_COLS)]
    lon_found = [original_name for lower_name, original_name in cols.items() if any(key in lower_name for key in POSSIBLE_LON_COLS)]

    if len(lat_found) == 1 and len(lon_found) == 1 and lat_found[0] != lon_found[0]:
        return {'success': True, 'columns': {'lat': lat_found[0], 'lon': lon_found[0]}}
    else:
        return {'ambiguous': True, 'all_columns': list(df.columns)}

def process_data(filepath, selected_cols=None):
    """
    Procesa el archivo de datos.
    """
    df = read_data_file(filepath)
    if isinstance(df, dict) and 'error' in df:
        return df

    if selected_cols:
        lat_col, lon_col = selected_cols['lat'], selected_cols['lon']
        if lat_col not in df.columns or lon_col not in df.columns:
            return {'error': 'Las columnas seleccionadas no se encontraron en el archivo.'}

        df.rename(columns={lat_col: '_lat', lon_col: '_lon'}, inplace=True)
        df['_lat'] = df['_lat'].astype(str).str.replace(',', '.', regex=False)
        df['_lon'] = df['_lon'].astype(str).str.replace(',', '.', regex=False)
        df['_lat'] = pd.to_numeric(df['_lat'], errors='coerce')
        df['_lon'] = pd.to_numeric(df['_lon'], errors='coerce')
        df.dropna(subset=['_lat', '_lon'], inplace=True)
        return df
    
    return analyze_columns(df)