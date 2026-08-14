from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi.responses import FileResponse, HTMLResponse
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright
from starlette.background import BackgroundTask

from app.config import settings
from app.errors import ExportError


async def build_pdf_file(template, context: dict) -> Path:
    html = template.render(**context)
    with NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8", dir=settings.export_dir) as html_file:
        html_file.write(html)
        html_path = Path(html_file.name)

    pdf_path = html_path.with_suffix(".pdf")
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page(viewport={"width": 1440, "height": 1080})
                await page.goto(html_path.as_uri(), wait_until="networkidle")
                await page.wait_for_function("window.__EXPORT_READY === true")
                await page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    landscape=True,
                    print_background=True,
                    margin={"top": "12mm", "right": "10mm", "bottom": "12mm", "left": "10mm"},
                )
            finally:
                await browser.close()
            await browser.close()
    except PlaywrightError as exc:
        raise ExportError(
            "No se pudo generar el PDF. Verifica que Chromium este instalado con `playwright install chromium` en el servidor.",
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
    return json.dumps(payload, ensure_ascii=False)


def remove_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def build_pdf_response(path: Path, filename: str) -> FileResponse:
    return FileResponse(path, filename=filename, media_type="application/pdf", background=BackgroundTask(remove_file, path))
