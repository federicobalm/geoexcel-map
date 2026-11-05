from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.errors import AppError
from app.models import ManualDatasetRequest, MapPreviewResponse, MapRequest, MapSummary, UploadSummary
import pandas as pd
from app.services.datasets import (
    build_points_payload,
    detect_coordinate_columns,
    prepare_dataframe,
    preview_rows,
    read_uploaded_table,
    suggest_category_columns,
    suggest_label_columns,
    validate_coordinates,
)
from app.services.exporters import (
    build_html_response,
    build_pdf_file,
    build_pdf_response,
    sanitize_filename,
    serialize_for_template,
)
from app.services.profiling import build_geographic_profile
from app.services.cartography import build_cartography, gaussian_density
from app.services.sessions import session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_store.ensure_dirs()
    session_store.cleanup_expired()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
templates = Jinja2Templates(directory=str(settings.project_root / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(settings.project_root / "app" / "static")), name="static")
app.mount("/sample_data", StaticFiles(directory=str(settings.project_root / "sample_data")), name="sample_data")


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    labels = {
        "cartographic_metadata": "Ficha del mapa", "event": "Titulo",
        "geographic_unit": "Unidad geográfica", "period_start": "Desde",
        "period_end": "Hasta", "author": "Analista o entidad",
        "synthetic": "Confirmación de datos ficticios", "period_confirmed": "Confirmación del período",
        "buffer_radius_m": "Buffer Rossmo (m)", "known_anchor_lat": "Latitud del anclaje",
        "known_anchor_lon": "Longitud del anclaje",
        "latitud": "Latitud", "longitud": "Longitud", "fecha": "Fecha", "hora": "Hora",
    }
    messages = []
    for error in exc.errors():
        field = str(error["loc"][-1]) if error["loc"] else "body"
        label = labels.get(field, "Configuración" if field == "body" else field)
        if 'events' in error['loc']:
            position = error['loc'].index('events') + 1
            if len(error['loc']) > position and isinstance(error['loc'][position], int):
                label = f"Evento {error['loc'][position] + 1} · {label}"
        message = error["msg"].removeprefix("Value error, ")
        if error["type"] == "missing":
            message = "Completa este campo."
        elif error["type"] == "string_too_short":
            message = f"Escribe al menos {error['ctx']['min_length']} caracteres."
        elif field in {"synthetic", "period_confirmed"}:
            message = "Marca esta confirmación para continuar."
        messages.append(f"{label}: {message}")
    return JSONResponse(status_code=422, content={"detail": " · ".join(messages)})


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"app_name": settings.app_name})


@app.get("/rossmo", response_class=HTMLResponse)
async def rossmo_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "rossmo.html", {"app_name": settings.app_name})


@app.get("/health/live")
async def health_live() -> dict:
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready() -> dict:
    return {"status": "ready"}


@app.post("/api/upload", response_model=UploadSummary)
async def upload_file(file: UploadFile = File(...)) -> UploadSummary:
    if not file.filename:
        raise AppError("Debes seleccionar un archivo.")

    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(f"El archivo supera el limite de {settings.max_upload_mb} MB.")

    raw_df = await asyncio.to_thread(read_uploaded_table, file.filename, content)
    return await asyncio.to_thread(_create_upload_summary, file.filename, raw_df)


@app.post('/api/manual-data', response_model=UploadSummary)
async def manual_data(data: ManualDatasetRequest) -> UploadSummary:
    records = [event.model_dump() for event in data.events]
    for index, record in enumerate(records, start=1):
        record['caso'] = record['caso'] or f'Evento {index}'
    return await asyncio.to_thread(_create_upload_summary, 'Carga_manual.csv', pd.DataFrame(records))


def _create_upload_summary(filename: str, raw_df: pd.DataFrame) -> UploadSummary:
    prepared_df = prepare_dataframe(raw_df)
    suggested_lat, suggested_lon, notes = detect_coordinate_columns(prepared_df)
    category_columns = suggest_category_columns(prepared_df)
    label_columns = suggest_label_columns(prepared_df)
    preview = preview_rows(prepared_df)

    session_id = session_store.create(
        filename,
        prepared_df,
        {
            "row_count": int(len(prepared_df)),
            "column_count": int(len(prepared_df.columns)),
            "columns": list(prepared_df.columns),
            "suggested_lat_column": suggested_lat,
            "suggested_lon_column": suggested_lon,
            "candidate_category_columns": category_columns,
            "candidate_label_columns": label_columns,
            "notes": notes,
        },
    )

    return UploadSummary(
        session_id=session_id,
        filename=filename,
        row_count=int(len(prepared_df)),
        column_count=int(len(prepared_df.columns)),
        columns=list(prepared_df.columns),
        preview_rows=preview,
        suggested_lat_column=suggested_lat,
        suggested_lon_column=suggested_lon,
        candidate_category_columns=category_columns,
        candidate_label_columns=label_columns,
        notes=notes,
    )


def _build_map_preview_payload(map_request: MapRequest) -> MapPreviewResponse:
    df = session_store.load_dataframe(map_request.session_id)
    cleaned_df, summary_data = validate_coordinates(df, map_request.lat_column, map_request.lon_column)
    if cleaned_df.empty:
        raise AppError("No hay coordenadas validas para generar un mapa. Revisa las columnas y el archivo.")
    points, popup_fields = build_points_payload(
        cleaned_df,
        map_request.lat_column,
        map_request.lon_column,
        map_request.label_column,
        map_request.category_column,
    )

    category_legend: list[dict[str, str]] = []
    if map_request.category_column:
        categories = sorted({point["category"] for point in points})
        palette = ["#526d82", "#698879", "#93805f", "#796c8f", "#647d85", "#a08183", "#72815b", "#876a57"]
        category_legend = [{"category": category, "color": palette[index % len(palette)]} for index, category in enumerate(categories)]

    profile = None
    if map_request.map_type == "profile":
        profile = build_geographic_profile(cleaned_df, map_request)

    summary = MapSummary(**summary_data)
    density = gaussian_density(cleaned_df, map_request.bandwidth_m) if map_request.map_type == "heatmap" else None
    cartography = build_cartography(map_request, summary, cleaned_df, density)
    if density is not None:
        # An exported density surface must not carry individual event coordinates/attributes.
        points, popup_fields, category_legend = [], [], []
    elif map_request.map_type == "proportional":
        points = [{'lat': float(lat), 'lon': float(lon), 'count': int(count), 'label': '', 'category': '', 'popup': {}}
                  for (lat, lon), count in cleaned_df.groupby(['lat', 'lon']).size().items()]
        popup_fields, category_legend = [], []

    return MapPreviewResponse(
        session_id=map_request.session_id,
        map_config=map_request,
        summary=summary,
        points=points,
        category_legend=category_legend,
        popup_fields=popup_fields,
        profile=profile,
        cartography=cartography,
        density=density,
    )


@app.post("/api/map-preview", response_model=MapPreviewResponse)
async def map_preview(map_request: MapRequest) -> MapPreviewResponse:
    return await asyncio.to_thread(_build_map_preview_payload, map_request)


def _build_export_payload(map_request: MapRequest) -> MapPreviewResponse:
    # Downloaded HTML and the PDF renderer use file://, which cannot supply the
    # HTTP Referer required by tile.openstreetmap.org. Choose an export basemap
    # before rendering so the map, attribution and report metadata agree.
    replace_osm = map_request.tile_layer == "OpenStreetMap"
    export_request = map_request.model_copy(update={"tile_layer": "Esri Light Gray"}) if replace_osm else map_request
    payload = _build_map_preview_payload(export_request)
    if replace_osm:
        payload.cartography["warnings"].append(
            "Fondo de exportación: Esri Light Gray sustituye a OpenStreetMap, "
            "cuyo servidor de teselas requiere una referencia HTTP que los archivos locales no envían. "
            "Los datos y la representación temática se conservan."
        )
    return payload


@app.post("/api/export/html")
async def export_html(map_request: MapRequest) -> HTMLResponse:
    preview_payload = await asyncio.to_thread(_build_export_payload, map_request)
    metadata = session_store.load_metadata(map_request.session_id)
    context = {
        "title": metadata["filename"],
        "title_json": json.dumps(metadata["filename"], ensure_ascii=False),
        "map_payload_json": serialize_for_template(preview_payload.model_dump()),
        "summary_json": json.dumps(preview_payload.summary.model_dump(), ensure_ascii=False),
    }
    filename = f"{sanitize_filename(metadata['filename'])}_{map_request.map_type}.html"
    return build_html_response(templates.get_template("export_map.html"), context, filename)


@app.post("/api/export/pdf")
async def export_pdf(map_request: MapRequest):
    preview_payload = await asyncio.to_thread(_build_export_payload, map_request)
    metadata = session_store.load_metadata(map_request.session_id)
    context = {
        "title": metadata["filename"],
        "title_json": json.dumps(metadata["filename"], ensure_ascii=False),
        "map_payload_json": serialize_for_template(preview_payload.model_dump()),
        "summary_json": json.dumps(preview_payload.summary.model_dump(), ensure_ascii=False),
    }
    pdf_path = await asyncio.to_thread(build_pdf_file, templates.get_template("export_pdf.html"), context)
    filename = f"{sanitize_filename(metadata['filename'])}_{map_request.map_type}.pdf"
    return build_pdf_response(pdf_path, filename)
