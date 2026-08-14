# GeoExcel Map v3

GeoExcel Map v3 es una herramienta web pensada para que alumnos trabajen con datos geograficos sin instalar Python, Git ni dependencias locales.

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

## Stack

1. `FastAPI` para backend.
2. `Leaflet` para mapa interactivo.
3. `pandas` para lectura y validacion de archivos.
4. `Playwright` para exportacion a PDF desde una vista controlada del servidor.

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

## Notas de producto

1. No hay cuentas de usuario en esta version.
2. La app trabaja con sesiones temporales del lado del servidor.
3. La validacion de coordenadas es una funcionalidad central, no un detalle secundario.
4. La exportacion PDF usa un navegador headless en el servidor, no en la maquina del alumno.
