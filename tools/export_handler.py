import os
import zipfile
import simplekml
import pandas as pd
import base64
import json
from flask import send_from_directory, render_template_string, flash
from datetime import datetime
from .excel_processor import process_excel
from .image_renderer import render_html_to_png, render_html_to_pdf
from .map_generator import create_map, create_heatmap_overlay

# Definir el directorio de datos para las rutas
DATA_DIR = os.path.join(os.getcwd(), 'data')
PROJECTS_DIR = os.path.join(DATA_DIR, 'projects')

def export_to_html(project):
    """Genera y envía un archivo HTML autocontenido."""
    temp_html_path = None
    try:
        df = process_excel(project.excel_path, project.get_lat_lon_cols())
        if df.empty:
            raise ValueError("No se encontraron datos válidos.")
        interactive_map = create_map(df, project.get_map_params(), project.get_lat_lon_cols(), is_for_export=False)
        temp_html_path = f"temp_export_{project.id}.html"
        interactive_map.save(temp_html_path)
        return send_from_directory(os.getcwd(), temp_html_path, as_attachment=True, download_name=f"{project.name}.html")
    except Exception as e:
        flash(f"Error al exportar HTML: {e}", "danger")
        return f"Error: {e}", 500
    finally:
        if temp_html_path and os.path.exists(temp_html_path):
            try: os.remove(temp_html_path)
            except OSError: pass

def export_to_pdf(project, user_info):
    """Genera y envía un PDF con una imagen estática del mapa."""
    png_path = None
    try:
        df = process_excel(project.excel_path, project.get_lat_lon_cols())
        if df.empty:
            raise ValueError("No se encontraron datos válidos.")
        map_params = project.get_map_params()
        clean_map = create_map(df, map_params, project.get_lat_lon_cols(), is_for_export=True)
        map_html = clean_map.get_root().render()
        
        png_path, _ = render_html_to_png(map_html, map_params.get('map_type'))
        with open(png_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        data_table_html = df.to_html(classes='table table-striped table-sm', index=False, border=0)
        full_html_for_pdf = render_template_string("""
        <html><head>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { font-family: sans-serif; }
                .header { text-align: center; padding: 10px; border-bottom: 1px solid #ccc; font-size: 10px; }
                .map-image { width: 100%; height: auto; page-break-after: always; }
                .table-container { page-break-before: always; padding: 20px; font-size: 8px; }
            </style></head>
            <body>
                <div class="header">
                    <strong>Título:</strong> {{ p.name }} | <strong>Autor:</strong> {{ u.nombre }} {{ u.apellido }} | <strong>Fecha:</strong> {{ date }}<br>
                    <strong>Tipo:</strong> {{ p.map_type }} | <strong>Norte:</strong> &uarr;
                </div>
                <img src="data:image/png;base64,{{ map_image_b64 }}" class="map-image">
                <div class="table-container"><h3>Tabla de Datos</h3>{{ data_table_html|safe }}</div>
            </body></html>
        """, p=project, u=user_info, date=datetime.now().strftime('%d-%m-%Y'), map_image_b64=encoded_string, data_table_html=data_table_html)
        
        pdf_path = render_html_to_pdf(full_html_for_pdf, map_params.get('map_type'))
        return send_from_directory(os.getcwd(), os.path.basename(pdf_path), as_attachment=True, download_name=f"{project.name}.pdf")
    except Exception as e:
        flash(f"Ocurrió un error al generar el PDF: {e}", "danger")
        return f"<h1>Error: {e}</h1>", 500
    finally:
        if png_path and os.path.exists(png_path):
            os.remove(png_path)

def export_to_kmz(project):
    """
    Exporta a KMZ. Para heatmaps, usa el overlay pre-generado.
    """
    try:
        kml = simplekml.Kml(name=project.name)
        
        if project.map_type == 'points':
            df = process_excel(project.excel_path, project.get_lat_lon_cols())
            if df.empty: raise ValueError("No hay puntos para exportar.")
            for _, row in df.iterrows():
                pnt = kml.newpoint(coords=[(row['_lon'], row['_lat'])])
                desc = ""
                for col, val in row.items():
                    if col not in ['_lat', '_lon']: desc += f"<b>{col}:</b> {val}<br>"
                pnt.description = desc
            
            kmz_path = os.path.join(DATA_DIR, f"export_{project.id}.kmz")
            kml.savekmz(kmz_path)
            return send_from_directory(DATA_DIR, os.path.basename(kmz_path), as_attachment=True, download_name=f"{project.name}.kmz")

        else: # Heatmap
            project_dir = os.path.join(PROJECTS_DIR, str(project.id))
            overlay_png_path = os.path.join(project_dir, 'overlay', 'overlay.png')
            bounds_json_path = os.path.join(project_dir, 'overlay', 'bounds.json')

            if not os.path.exists(overlay_png_path) or not os.path.exists(bounds_json_path):
                raise FileNotFoundError("No se encontró el archivo de overlay pre-generado. Por favor, guarde el proyecto de nuevo.")
            
            with open(bounds_json_path, 'r') as f:
                bounds = json.load(f)

            overlay = kml.newgroundoverlay(name=f"Capa {project.map_type}")
            overlay.icon.href = 'overlay.png'
            overlay.latlonbox.north, overlay.latlonbox.south = bounds['north'], bounds['south']
            overlay.latlonbox.east, overlay.latlonbox.west = bounds['east'], bounds['west']
            
            zip_filename = f"{project.name}_kmz.zip"
            zip_path = os.path.join(DATA_DIR, zip_filename)
            kml_path = os.path.join(DATA_DIR, "doc.kml")
            kml.save(kml_path)

            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.write(kml_path, arcname="doc.kml")
                zf.write(overlay_png_path, arcname="overlay.png")
            
            if os.path.exists(kml_path): os.remove(kml_path)

            return send_from_directory(DATA_DIR, zip_filename, as_attachment=True, download_name=zip_filename)
    
    except Exception as e:
        flash(f"Error al exportar KMZ: {e}", "danger")
        return f"<h1>Error: {e}</h1>", 500