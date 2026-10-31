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

## Uso exclusivamente académico · resultados simulados

> **Todos los mapas, análisis, estimaciones y resultados generados por GeoExcel Map son simulaciones destinadas exclusivamente a la enseñanza y al aprendizaje con datos ficticios.**
>
> **Bajo ningún motivo representan una investigación real ni forman parte de un procedimiento de acusación. No constituyen evidencia, prueba pericial ni fundamento para imputar, acusar o atribuir responsabilidad a persona alguna. No deben utilizarse para esos fines.**
>
> Los informes HTML y PDF incluyen expresamente esta aclaración. La aplicación debe utilizarse únicamente con datos ficticios para ejercicios académicos.

## Instalación para alumnos · Windows

En **Windows 10/11 de 64 bits**, abrí **PowerShell** (sin ejecutar como administrador), pegá este único comando y presioná Enter:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/federicobalm/geoexcel-map/main/scripts/install.ps1 | iex"
```

El instalador descarga GeoExcel Map, prepara Python si hace falta, instala las dependencias y Chromium para generar PDF, y crea el acceso directo **GeoExcel Map** en tu escritorio con el icono de la aplicación. No necesitás Git ni preparar un entorno virtual.

- Esperá el mensaje **Listo**; la primera instalación puede tardar varios minutos.
- Hacé doble clic en **GeoExcel Map**. El navegador se abre cuando el servidor está listo.
- Dejá abierta la ventana del servidor mientras trabajás. Para finalizar, presioná `Ctrl+C` en esa ventana.
- Para actualizar, cerrá la aplicación y volvé a ejecutar el mismo comando.
- Se instala para tu usuario en `%LOCALAPPDATA%\GeoExcel-Map`. Conserva los datos locales al actualizar.
- Se necesita Internet para instalar y para cargar las bibliotecas y los mapas de fondo, también al abrir un HTML exportado o generar un PDF.
- Al exportar HTML o PDF, el fondo OpenStreetMap se sustituye por **Esri claro**: los archivos locales no envían la referencia HTTP exigida por el servidor de OpenStreetMap. El informe identifica el fondo utilizado; los datos y las capas temáticas se conservan. Los otros fondos seleccionados se mantienen.

El instalador aprovecha Python 3.11–3.13 cuando está disponible mediante `py`; en caso contrario instala Python 3.12 de python.org para el usuario, verificando su firma digital.

## Vista general

1. Cargas un `csv` o `xlsx`.
2. La app sugiere columnas de latitud y longitud.
3. Valida filas problemáticas y resume errores.
4. Genera mapas de puntos, calor clásico, KDE, coropleta por grilla, proporcionales, cluster o categoria.
5. Puede ejecutar perfilado geografico criminal con el algoritmo CGT de Rossmo.
6. Exporta el resultado como `HTML` o `PDF`.

Las exportaciones conservan el **centro y el nivel de zoom** que estás usando al pulsar Descargar. Acercá y desplazá el mapa antes de exportar para elegir la vista inicial del HTML y la vista del PDF. En Rossmo se conserva la vista elegida en el paso de previsualización.

## Objetivo

Permitir este flujo con la menor friccion posible:

1. Subir un archivo `xlsx` o `csv`.
2. Validar coordenadas y detectar errores de carga.
3. Generar mapas utiles para analisis en clase.
4. Exportar el resultado a `HTML` o `PDF`.

## Tipos de mapa incluidos

1. Puntos.
2. Densidad KDE gaussiana local (ancho de banda en metros; eventos/km²).
3. Puntos agrupados.
4. Puntos por categoria.
5. Perfil geografico criminal.
6. Símbolos proporcionales: área del círculo proporcional a la frecuencia de eventos por coordenada coincidente.
7. **Mapa de calor / Hot map**: paleta clásica azul → cian → verde → amarillo → rojo, con radio y niveles ajustables.
8. **Coropleta por grilla**: cantidad de eventos por celda en una grilla de 7 × 7, con leyenda de conteos.

### Reglas cartográficas para el aula

La ficha pide **Titulo**, unidad geográfica, fechas de inicio/fin, analista o entidad y las confirmaciones de datos ficticios y período. El período es una declaración del analista: no se verifican ni filtran fechas individuales de la planilla. Cada fila debe representar un evento.

- Puntos, categorías y agrupaciones admiten el período indicado, sin límite de días impuesto por la aplicación.
- Coropleta por grilla: representa conteos de eventos sobre la extensión de los datos, con cinco clases relativas al máximo. Las celdas vacías quedan sin colorear. Las celdas no son barrios ni límites administrativos y los valores no son tasas poblacionales.
- Hot map: muestra concentración relativa mediante suavizado en pantalla. La intensidad depende del radio y del zoom; no equivale a eventos/km².
- KDE: aproximación gaussiana con binning y evaluación en una grilla de 96 × 96, UTM local, sin corrección de borde. Extensión máxima 300 km por eje; rechaza anchos de banda incompatibles con la resolución. El HTML exporta la superficie, no coordenadas/atributos individuales.
- Paleta clásica para Hot map y azules por defecto para KDE; también disponibles verdes azulados, Viridis y grises. Los niveles de color son intensidades relativas, no percentiles ni probabilidades.
- Vistas y exportaciones incorporan título, autor y elaboración UTC, leyenda con fuentes y método, norte, escala gráfica y porcentaje de coordenadas válidas sobre el total. Esta cobertura no certifica geocodificación de direcciones ni precisión posicional.
- Coordenadas repetidas generan un aviso para revisar centroides, alturas imputadas y duplicados. No es una detección automática del sesgo de dirección incompleta.
- Las concentraciones no prueban causalidad; las hipótesis deben contrastarse con evidencia y teoría. La agregación por sí sola no acredita anonimato ni cumplimiento legal.

Pruebas de las reglas: `python -m unittest discover -s tests -v`.

Prueba de navegador con el servidor en marcha: `python tools/verify_flows.py --url http://127.0.0.1:8000`. Recorre todos los tipos de mapa, el asistente Rossmo, errores de validación y exportaciones HTML/PDF. Requiere Chromium instalado y conexión a los proveedores de mapas.

## Perfilado geografico criminal

1. Implementa una superficie de jeopardy basada en el algoritmo CGT de Rossmo.
2. Proyecta coordenadas WGS84 a UTM antes del calculo.
3. Permite elegir distancia `manhattan` o `euclidean` segun el entorno.
4. Usa una grilla fija de `200 x 200` celdas para estimar el punto de anclaje.
5. Expone `buffer`, exponentes `f` y `g`, constante `k` y HS% retrospectivo opcional.

## Datos de ejemplo

1. `sample_data/plantilla_geoexcel_map.csv` sirve para probar el flujo completo.
2. `sample_data/ejemplo.xlsx` queda como referencia de formato alternativo.
3. `sample_data/serie_rossmo_demo.csv` sirve para probar el perfilador con una serie vinculada de 6 hechos.

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

## Autoría

Desarrollado por **Federico Balmaceda**.

Repositorio: [github.com/federicobalm/geoexcel-map](https://github.com/federicobalm/geoexcel-map).
