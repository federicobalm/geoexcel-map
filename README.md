# GeoExcel Map: Mapeo Profesional desde Excel

![License](https://img.shields.io/badge/License-MIT-blue.svg)

**GeoExcel Map** es una aplicación de escritorio diseñada para transformar, con solo un par de clics, hojas de cálculo de Excel con coordenadas geográficas en mapas interactivos y profesionales.

Creada especialmente para los alumnos de la **Licenciatura en Criminalística y Estudios Forenses**, esta herramienta elimina la complejidad de los sistemas de información geográfica (SIG) tradicionales, permitiendo a cualquier estudiante analizar y visualizar datos geoespaciales de forma rápida e intuitiva.

---

## Galería de Funcionalidades

| Mapa de Puntos (OSM) | Mapa de Calor (Satelital) | Interfaz Limpia (Modo Oscuro) |
| :---: | :---: | :---: |
| ![Vista de Puntos en OpenStreetMap](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/puntos_agrupados_-_osm.png?raw=true) | ![Vista de Heatmap en Esri World Imagery](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/heat_-_esri_world.png?raw=true) | ![Interfaz principal en modo oscuro](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/home_dark_mode.png?raw=true) |
| **Mapa de Puntos (CartoDB)** | **Mapa de Calor (CartoDB)** | **Opciones de Exportación** |
| ![Vista de Puntos en CartoDB Positron](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/puntos_agrupados_-_cartodb_positron.png?raw=true) | ![Vista de Heatmap en CartoDB Dark Matter](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/heat_-_cartodb.png?raw=true) | ![Vista de un proyecto con sus opciones de exportación](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/full_heat_and_export_options.png?raw=true) |

---

## Características Principales

*   🗺️ **Mapas de Puntos Individuales**: Visualiza cada punto de tu Excel con un icono personalizado.
*   🔥 **Mapas de Calor (Heatmaps)**: Descubre zonas de alta concentración de eventos con mapas de calor dinámicos.
*   💾 **Gestión de Proyectos**: Guarda tus mapas, configuraciones y datos para reabrirlos más tarde.
*   📤 **Exportación Profesional**: Comparte tus resultados en formatos listos para usar en informes y presentaciones:
    *   **HTML**: Un archivo 100% portable que funciona en cualquier navegador.
    *   **PDF**: Un informe cartográfico profesional con encabezado y tabla de datos.
    *   **KMZ**: Compatible con Google Earth Pro, con overlays transparentes para heatmaps.
*   🎨 **Personalización Completa**: Elige entre múltiples capas de mapa base (callejeros, satelitales, etc.).
*   🔒 **100% Local y Privado**: Todos tus datos se guardan exclusivamente en tu computadora.

---

## Instalación

Para que GeoExcel Map funcione, tu sistema necesita dos herramientas gratuitas muy comunes. El instalador verificará si las tienes y te guiará si falta alguna.

### Requisitos Previos

| Herramienta | Propósito | Enlace de Descarga |
| :--- | :--- | :--- |
| **Python** | El "motor" de la aplicación. | [![Descargar Python](https://img.shields.io/badge/Descargar-Python-blue?style=for-the-badge&logo=python)](https://www.python.org/downloads/) |
| **Git** | Para descargar el código del proyecto. | [![Descargar Git](https://img.shields.io/badge/Descargar-Git-orange?style=for-the-badge&logo=git)](https://git-scm.com/downloads/) |

> **¡MUY IMPORTANTE!** Durante la instalación de **Python** en Windows, asegúrate de marcar la casilla que dice **"Add Python.exe to PATH"** en la primera pantalla del instalador.

### Métodos de Instalación

Elige **uno** de los siguientes métodos. El Método 1 es el más rápido.

#### Método 1: Instalación Rápida con Comando (Recomendado)

1.  **Crea una carpeta nueva y vacía** donde quieras instalar la aplicación (ej: en tu Escritorio o en `Documentos`).
2.  **Abre una terminal en esa carpeta:**
    *   **Windows:** Abre el **Símbolo del Sistema (CMD) como Administrador**.
    *   **macOS/Linux:** Abre la **Terminal**.
3.  **Ejecuta el comando** correspondiente a tu sistema operativo:

    **Para Windows:**
    ```cmd
    curl -L https://raw.githubusercontent.com/federicobalm/geoexcel-map/main/install.bat -o install.bat && call install.bat
    ```

    **Para macOS y Linux:**
    ```bash
    curl -L https://raw.githubusercontent.com/federicobalm/geoexcel-map/main/install.sh -o install.sh && bash install.sh
    ```

#### Método 2: Descarga Manual del ZIP

Si prefieres no usar la terminal para la descarga inicial:

1.  **Descarga el proyecto** haciendo clic en el siguiente botón:
    <br>
    <a href="https://github.com/federicobalm/geoexcel-map/archive/refs/heads/main.zip" target="_blank">
      <img src="https://img.shields.io/badge/Descargar_Proyecto-ZIP-brightgreen?style=for-the-badge&logo=github" alt="Descargar ZIP">
    </a>
    <br><br>
2.  **Descomprime el archivo ZIP** en una carpeta permanente de tu elección.
3.  **Ejecuta el instalador** que se encuentra dentro de la carpeta que acabas de descomprimir:
    *   **Windows:** Haz clic derecho en `install.bat` y selecciona **"Ejecutar como administrador"**.
    *   **macOS/Linux:** Abre una terminal en la carpeta y ejecuta `bash install.sh`.

El script se encargará del resto, configurando todo lo necesario para que la aplicación funcione.

---

## Cómo Usar la Aplicación

Una vez instalada, para volver a abrirla:

*   **Windows:** Usa el **acceso directo "GeoExcel Map"** que se creó en tu Escritorio, o haz doble clic en `run.bat` dentro de la carpeta del proyecto.
*   **macOS / Linux:** Abre una terminal y ejecuta `./run.sh` desde la carpeta del proyecto. Si creaste el alias, simplemente escribe `geoexcel` en cualquier terminal nueva.

---

## Autor y Soporte

Este proyecto ha sido ideado y desarrollado por el **Lic. Mg. Federico Balmaceda** ([federicobalm@gmail.com](mailto:federicobalm@gmail.com)).

Es un proyecto personal mantenido de forma voluntaria. Como tal, **no se ofrece soporte técnico directo**. Las actualizaciones se realizarán según la disponibilidad de tiempo. Si encuentras un error, te animamos a abrir un "Issue" en la pestaña correspondiente de GitHub.

## Licencia

Este proyecto es de código abierto y se distribuye bajo la **Licencia MIT**.