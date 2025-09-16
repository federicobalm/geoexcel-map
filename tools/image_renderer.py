import os
import time
import base64
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def get_driver(transparent=False):
    """Configura un driver de Chrome headless."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--hide-scrollbars")
    if transparent:
        chrome_options.add_argument("--transparent-headless")
        chrome_options.add_argument("--disable-gpu")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def wait_for_map_data(driver, map_type):
    """
    Espera explícitamente a que los elementos del mapa estén visibles.
    """
    timeout = 20
    wait = WebDriverWait(driver, timeout)
    try:
        # Esperar a que los tiles del mapa base se carguen
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.leaflet-tile-loaded")))
        
        # Ahora, esperar por la capa de datos específica
        if map_type == 'points':
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".custom-div-icon")))
        elif map_type == 'heatmap':
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "canvas.leaflet-heatmap-layer")))
        elif map_type == 'choropleth':
            # --- LÓGICA FALTANTE AÑADIDA ---
            # Esperar a que los polígonos SVG de la coropleta se rendericen
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "path.leaflet-interactive")))
        
        # Damos un respiro extra para que el renderizado finalice
        time.sleep(2)
        
    except Exception as e:
        print(f"ADVERTENCIA: Tiempo de espera agotado al buscar elementos del mapa. La exportación podría estar incompleta. Error: {e}")

def capture_heatmap_canvas_and_bounds(html_content, output_path='overlay.png'):
    """
    Renderiza un mapa de calor, extrae el canvas y obtiene las coordenadas reales.
    """
    temp_html_path = 'temp_heatmap_for_capture.html'
    with open(temp_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    driver = get_driver(transparent=True)
    try:
        driver.get(f"file:///{os.path.abspath(temp_html_path)}")
        wait_for_map_data(driver, 'heatmap')

        bounds_script = """
        for (let key in this) { if (this[key] instanceof L.Map) {
            const bounds = this[key].getBounds();
            return {'south': bounds.getSouth(),'west': bounds.getWest(),'north': bounds.getNorth(),'east': bounds.getEast()};
        }} return null;"""
        bounds = driver.execute_script(bounds_script)
        if not bounds:
            raise Exception("No se pudo obtener las coordenadas del mapa para el KMZ.")

        canvas_script = """
            const canvas = document.querySelector('canvas.leaflet-heatmap-layer');
            if (!canvas) { return null; }
            return canvas.toDataURL('image/png');
        """
        image_data_url = driver.execute_script(canvas_script)
        if not image_data_url:
            raise Exception("No se pudo encontrar el canvas del heatmap para capturar.")
        
        header, encoded = image_data_url.split(",", 1)
        png_data = base64.b64decode(encoded)
        with open(output_path, 'wb') as f:
            f.write(png_data)
            
    finally:
        driver.quit()
        if os.path.exists(temp_html_path):
            os.remove(temp_html_path)
    
    return bounds

def render_html_to_png(html_content, map_type):
    """Renderiza un mapa COMPLETO a PNG (para PDF)."""
    temp_html_path = 'temp_map_for_png.html'
    output_png_path = 'temp_map_render.png'
    with open(temp_html_path, 'w', encoding='utf-8') as f: f.write(html_content)
    driver = get_driver()
    try:
        driver.get(f"file:///{os.path.abspath(temp_html_path)}"); wait_for_map_data(driver, map_type)
        bounds_script = """
        for (let key in this) { if (this[key] instanceof L.Map) {
            const bounds = this[key].getBounds();
            return {'south': bounds.getSouth(),'west': bounds.getWest(),'north': bounds.getNorth(),'east': bounds.getEast()};
        }} return null;"""
        bounds = driver.execute_script(bounds_script)
        if not bounds: raise Exception("No se pudo obtener las coordenadas del mapa.")
        driver.save_screenshot(output_png_path)
    finally:
        driver.quit()
        if os.path.exists(temp_html_path): os.remove(temp_html_path)
    return output_png_path, bounds

def render_html_to_pdf(html_content, map_type):
    """Renderiza HTML a PDF."""
    temp_html_path = 'temp_map_for_pdf.html'
    output_pdf_path = 'temp_map_render.pdf'
    with open(temp_html_path, 'w', encoding='utf-8') as f: f.write(html_content)
    driver = get_driver()
    try:
        driver.get(f"file:///{os.path.abspath(temp_html_path)}"); wait_for_map_data(driver, map_type)
        print_options = {'landscape': True, 'printBackground': True, 'pageSize': 'A4'}
        result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
        pdf_data = base64.b64decode(result['data'])
        with open(output_pdf_path, 'wb') as f: f.write(pdf_data)
    finally:
        driver.quit()
        if os.path.exists(temp_html_path): os.remove(temp_html_path)
    return output_pdf_path