<div align="center">
  <img src="https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/logo/GeoExcel-Map.png?raw=true" width="140" alt="GeoExcel Map logo">
  <h1>GeoExcel Map v3</h1>
  <p><strong>De planilla a mapa interactivo, validado y exportable en minutos.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/FastAPI-v3-009688?style=flat-square" alt="FastAPI v3">
    <img src="https://img.shields.io/badge/Leaflet-maps-199900?style=flat-square" alt="Leaflet">
    <img src="https://img.shields.io/badge/Playwright-PDF-7A42F4?style=flat-square" alt="Playwright PDF">
    <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Licencia-MIT-green?style=flat-square" alt="MIT">
  </p>
</div>

GeoExcel Map v3 es una herramienta web pensada para que alumnos y equipos docentes trabajen con datos geograficos sin depender de SIG pesados ni flujos manuales de limpieza previos.

## Vista general

1. Cargas un `csv` o `xlsx`.
2. La app sugiere columnas de latitud y longitud.
3. Valida filas problemáticas y resume errores.
4. Genera mapas de puntos, calor, cluster o categoria.
5. Exporta el resultado como `HTML` o `PDF`.

## Capturas

| Interfaz principal | Validacion guiada | Exportacion y resultados |
| :---: | :---: | :---: |
| ![Interfaz principal](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/home_dark_mode.png?raw=true) | ![Validacion guiada](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/deteccion_columnas.png?raw=true) | ![Resultados y exportacion](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/full_heat_and_export_options.png?raw=true) |

## Objetivo

Permitir este flujo con la menor friccion posible:

1. Subir un archivo `xlsx` o `csv`.
2. Validar coordenadas y detectar errores de carga.
3. Generar mapas utiles para analisis en clase.
4. Exportar el resultado a `HTML` o `PDF`.

## Tipos de mapa incluidos

1. Puntos.
2. Mapa de calor.
3. Puntos agrupados.
4. Puntos por categoria.

## Casos de uso

1. Analisis territorial en entornos educativos.
2. Trabajo con hechos criminalisticos o forenses georreferenciados.
3. Revision rapida de calidad de coordenadas antes de compartir resultados.
4. Entrega de mapas exportables sin pedir al alumno herramientas extra.

## Stack

1. `FastAPI` para backend.
2. `Leaflet` para mapa interactivo.
3. `pandas` para lectura y validacion de archivos.
4. `Playwright` para exportacion a PDF desde una vista controlada del servidor.

## Arranque rapido

```bash
python -m venv .venv
pip install -r requirements.txt
playwright install chromium
python app.py
```

Luego abre `http://127.0.0.1:8000`.

## Desarrollo local

1. Crear entorno virtual.
2. Instalar dependencias.
3. Instalar Chromium para Playwright.
4. Ejecutar la app.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python app.py
```

En Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python app.py
```

La aplicacion queda disponible en `http://127.0.0.1:8000`.

Tambien puedes arrancarla con `uvicorn app.main:app --reload`, pero `python app.py` ya respeta `app_host`, `app_port` y `app_env` desde `app/config.py` o `.env`.

## Flujo funcional

1. `POST /api/upload` lee el archivo y crea una sesion temporal.
2. `POST /api/map-preview` valida coordenadas y arma el payload del mapa.
3. `POST /api/export/html` genera una exportacion interactiva descargable.
4. `POST /api/export/pdf` renderiza una vista controlada y la imprime a PDF.

## Estructura

```text
app/
  __init__.py
  main.py
  config.py
  errors.py
  models.py
  services/
  static/
  templates/
sample_data/
data/
```

## Datos de ejemplo

1. `sample_data/plantilla_geoexcel_map.csv` sirve para probar el flujo completo.
2. `sample_data/ejemplo.xlsx` queda como referencia de formato alternativo.

Ejemplo de plantilla:

```csv
caso,latitud,longitud,tipo,zona,descripcion
Caso 1,-34.6037,-58.3816,Robo,Centro,Hecho en zona comercial
Caso 2,-34.6158,-58.4333,Hurto,Sur,Registro cercano a avenida principal
```

## Notas de producto

1. No hay cuentas de usuario en esta version.
2. La app trabaja con sesiones temporales del lado del servidor.
3. La validacion de coordenadas es una funcionalidad central, no un detalle secundario.
4. La exportacion PDF usa un navegador headless en el servidor, no en la maquina del alumno.

## Estado actual

1. La version actual reemplaza la arquitectura anterior por una base `FastAPI` mas simple de extender.
2. El flujo principal ya cubre carga, validacion, visualizacion y exportacion.
3. La base quedo preparada para sumar implementaciones mas grandes encima de esta v3.
