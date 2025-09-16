<div align="center">
  <img src="URL_DE_TU_LOGO_SI_TIENES_UNO" width="150">
  <h1>GeoExcel Map v2.0</h1>
  <p><strong>Mapeo Profesional e Inteligente desde Cualquier Archivo de Datos</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Versión-2.0-blue.svg" alt="Version">
    <img src="https://img.shields.io/badge/Licencia-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/Python-3.8+-brightgreen.svg?logo=python" alt="Python Version">
  </p>
</div>

**GeoExcel Map** es una aplicación de escritorio diseñada para transformar, con solo un par de clics, hojas de cálculo y archivos de texto con coordenadas geográficas en mapas interactivos y profesionales.

Creada especialmente para los alumnos de la **Licenciatura en Criminalística y Estudios Forenses**, esta herramienta elimina la complejidad de los sistemas de información geográfica (SIG) tradicionales, permitiendo a cualquier estudiante analizar y visualizar datos geoespaciales de forma rápida e intuitiva.

---

## ✨ Novedades de la Versión 2.0: El Salto a la Inteligencia

Esta actualización masiva se centra en la facilidad de uso y la flexibilidad, eliminando las barreras para el análisis de datos.

*   🧠 **Motor de Carga Inteligente:**
    *   <img src="https://img.shields.io/badge/Soporte_Multiformato-.-blue?style=for-the-badge" alt="Soporte"> **.xlsx, .xls, .csv, y .txt**.
    *   <img src="https://img.shields.io/badge/Detección_Automática-.-green?style=for-the-badge" alt="Detección"> El sistema analiza tu archivo y **detecta automáticamente** las columnas de `latitud` y `longitud`, sin importar cómo las hayas nombrado.
    *   <img src="https://img.shields.io/badge/Selección_Guiada-.-yellow?style=for-the-badge" alt="Selección"> Si el sistema tiene dudas (o si tu archivo no tiene encabezados), te presentará una **interfaz visual para que elijas las columnas correctas** con un solo clic.
    *   <img src="https://img.shields.io/badge/Tolerancia_de_Formato-.-orange?style=for-the-badge" alt="Tolerancia"> Reconoce coordenadas con punto (`-34.5`) o coma (`-34,5`) y separadores de CSV por coma o punto y coma.

*   💅 **Instaladores Mejorados:** Scripts de instalación con una interfaz visual más profesional en la consola, con colores y guías claras.

---

## 갤러리 Galería de Funcionalidades

| Mapa de Puntos (OSM) | Mapa de Calor (Satelital) | Selección de Columnas Inteligente |
| :---: | :---: | :---: |
| ![Vista de Puntos en OpenStreetMap](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/puntos_agrupados_-_osm.png?raw=true) | ![Vista de Heatmap en Esri World Imagery](https://github.com/federicobalm/geoexcel-map/blob/main/static/resources/screenshot/heat_-_esri_world.png?raw=true) | ![Interfaz de selección de columnas](https://i.imgur.com/URL_DE_LA_IMAGEN_DE_SELECCION.png) |

---

## ⚙️ Instalación

Para que GeoExcel Map funcione, tu sistema necesita dos herramientas gratuitas muy comunes. El instalador verificará si las tienes y te guiará si falta alguna.

### Requisitos Previos

| Herramienta | Propósito | Enlace de Descarga |
| :--- | :--- | :--- |
| **Python** | El "motor" de la aplicación. | [![Descargar Python](https://img.shields.io/badge/Descargar-Python-blue?style=for-the-badge&logo=python)](https://www.python.org/downloads/) |
| **Git** | Para descargar el código. | [![Descargar Git](https://img.shields.io/badge/Descargar-Git-orange?style=for-the-badge&logo=git)](https://git-scm.com/downloads/) |

> <div style="background-color: rgba(255, 0, 0, 0.1); border-left: 5px solid red; padding: 10px;">
>   <strong>¡MUY IMPORTANTE (Windows)!</strong> Durante la instalación de <strong>Python</strong>, asegúrate de marcar la casilla <strong>"Add Python.exe to PATH"</strong> en la primera pantalla del instalador.
> </div>

### Métodos de Instalación

Elige **uno** de los siguientes métodos. El Método 1 es el más rápido.

#### Método 1: Instalación Rápida con Comando (Recomendado)

1.  **Crea una carpeta nueva y vacía** donde quieras instalar la aplicación.
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

## 🚀 Cómo Usar la Aplicación

Una vez instalada, para volver a abrirla:

*   **Windows:** Usa el **acceso directo "GeoExcel Map"** que se creó en tu Escritorio.
*   **macOS / Linux:** Abre una terminal y ejecuta `./run.sh` desde la carpeta del proyecto (o usa el alias `geoexcel` si lo creaste).

---

## ✍️ Autor y Soporte

Este proyecto ha sido ideado y desarrollado por el **Lic. Mg. Federico Balmaceda** ([federicobalm@gmail.com](mailto:federicobalm@gmail.com)).

Es un proyecto personal mantenido de forma voluntaria. No se ofrece soporte técnico directo. Si encuentras un error, te animamos a abrir un "Issue" en la pestaña correspondiente de GitHub.

## 📜 Licencia

Este proyecto es de código abierto y se distribuye bajo la **Licencia MIT**.