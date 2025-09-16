import requests
import json
import os
import hashlib
import osm2geojson
import pandas as pd

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'boundaries')
os.makedirs(CACHE_DIR, exist_ok=True)

SCOPE_TO_ADMIN_LEVEL = {
    'province': '4', 'department': '6', 'suburb': '8'
}

def get_cached_geojson(key):
    filepath = os.path.join(CACHE_DIR, f"{key}.geojson")
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f: return json.load(f)
    return None

def save_geojson_to_cache(key, data):
    filepath = os.path.join(CACHE_DIR, f"{key}.geojson")
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(data, f)

def analyze_points(df):
    sample_df = df.sample(n=min(len(df), 10))
    countries, states, counties = set(), set(), set()
    
    for _, row in sample_df.iterrows():
        params = {'lat': row['_lat'], 'lon': row['_lon'], 'format': 'json', 'addressdetails': 1}
        headers = {'User-Agent': 'GeoExcelMap/1.0'}
        try:
            response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            address = response.json().get('address', {})
            
            if address.get('country'): countries.add(address.get('country'))
            if address.get('state'): states.add(address.get('state'))
            if address.get('county'): counties.add(address.get('county'))
        except requests.RequestException as e:
            print(f"Error de geocodificación inversa: {e}")
            continue

    return {
        "countries": sorted(list(countries)),
        "states": sorted(list(states)),
        "counties": sorted(list(counties))
    }

def fetch_boundaries(scope, container_name):
    admin_level = SCOPE_TO_ADMIN_LEVEL.get(scope)
    if not admin_level:
        raise ValueError(f"Ámbito no válido: {scope}")

    cache_key = hashlib.md5(f"{scope}_{container_name}".encode()).hexdigest()
    cached_data = get_cached_geojson(cache_key)
    if cached_data:
        print(f"Cargando '{scope} de {container_name}' desde cache.")
        return cached_data

    print(f"Consultando Overpass API para '{scope} de {container_name}'...")
    query = f"""
    [out:json][timeout:180];
    area[name="{container_name}"]->.searchArea;
    (relation(area.searchArea)[boundary="administrative"][admin_level="{admin_level}"];);
    out body; >; out skel qt;
    """
    response = requests.post(OVERPASS_URL, data={'data': query})
    response.raise_for_status()
    
    geojson_data = osm2geojson.json2geojson(response.json())
    for feature in geojson_data.get('features', []):
        tags = feature.get('properties', {}).get('tags', {})
        if 'name' in tags:
            feature['properties']['nombre'] = tags['name']
    
    if geojson_data.get('features'):
        save_geojson_to_cache(cache_key, geojson_data)
    
    return geojson_data