from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi.responses import FileResponse, HTMLResponse
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from starlette.background import BackgroundTask

from app.config import settings
from app.errors import ExportError


def build_pdf_file(template, context: dict) -> Path:
    html = template.render(**context)
    with NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8", dir=settings.export_dir) as html_file:
        html_file.write(html)
        html_path = Path(html_file.name)

    pdf_path = html_path.with_suffix(".pdf")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 1080})
                page.goto(html_path.as_uri(), wait_until="networkidle")
                page.wait_for_function("window.__EXPORT_READY === true")
                page.wait_for_function("""() => {
                    const tiles = [...document.querySelectorAll('#map img.leaflet-tile')];
                    return tiles.length > 0 && tiles.every(tile => tile.complete && tile.naturalWidth > 0);
                }""", timeout=30000)
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    landscape=True,
                    print_background=True,
                    margin={"top": "12mm", "right": "10mm", "bottom": "12mm", "left": "10mm"},
                )
            finally:
                browser.close()
    except (PlaywrightError, NotImplementedError, OSError) as exc:
        raise ExportError(
            "No se pudo completar el PDF. Verifica la conexion al proveedor del mapa o prueba otro fondo. Si Chromium no esta instalado, ejecuta `playwright install chromium` y reinicia la aplicacion.",
            status_code=500,
        ) from exc
    finally:
        if html_path.exists():
            html_path.unlink()

    return pdf_path


def build_html_response(template, context: dict, filename: str) -> HTMLResponse:
    html = template.render(**context)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return HTMLResponse(content=html, headers=headers)


def sanitize_filename(raw_name: str) -> str:
    cleaned = "_".join(Path(raw_name).stem.strip().split()).lower()
    return cleaned or "geoexcel_map"


def serialize_for_template(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def remove_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def build_pdf_response(path: Path, filename: str) -> FileResponse:
    return FileResponse(path, filename=filename, media_type="application/pdf", background=BackgroundTask(remove_file, path))
