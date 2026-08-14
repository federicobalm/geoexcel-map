from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.errors import AppError
from app.models import MapPreviewResponse, MapRequest, MapSummary, UploadSummary
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


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {"app_name": settings.app_name})


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
    prepared_df = await asyncio.to_thread(prepare_dataframe, raw_df)
    suggested_lat, suggested_lon, notes = await asyncio.to_thread(detect_coordinate_columns, prepared_df)
    category_columns = await asyncio.to_thread(suggest_category_columns, prepared_df)
    label_columns = await asyncio.to_thread(suggest_label_columns, prepared_df)
    preview = await asyncio.to_thread(preview_rows, prepared_df)

    session_id = session_store.create(
        file.filename,
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
        filename=file.filename,
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
        palette = ["#e63946", "#457b9d", "#f4a261", "#2a9d8f", "#6d597a", "#ffb703", "#8ecae6", "#bc4749"]
        category_legend = [{"category": category, "color": palette[index % len(palette)]} for index, category in enumerate(categories)]

    profile = None
    if map_request.map_type == "profile":
        profile = build_geographic_profile(cleaned_df, map_request)

    return MapPreviewResponse(
        session_id=map_request.session_id,
        map_config=map_request,
        summary=MapSummary(**summary_data),
        points=points,
        category_legend=category_legend,
        popup_fields=popup_fields,
        profile=profile,
    )


@app.post("/api/map-preview", response_model=MapPreviewResponse)
async def map_preview(map_request: MapRequest) -> MapPreviewResponse:
    return await asyncio.to_thread(_build_map_preview_payload, map_request)


@app.post("/api/export/html")
async def export_html(map_request: MapRequest) -> HTMLResponse:
    preview_payload = await asyncio.to_thread(_build_map_preview_payload, map_request)
    metadata = session_store.load_metadata(map_request.session_id)
    context = {
        "title": metadata["filename"],
        "map_payload_json": serialize_for_template(preview_payload.model_dump()),
        "summary_json": json.dumps(preview_payload.summary.model_dump(), ensure_ascii=False),
    }
    filename = f"{sanitize_filename(metadata['filename'])}_{map_request.map_type}.html"
    return build_html_response(templates.get_template("export_map.html"), context, filename)


@app.post("/api/export/pdf")
async def export_pdf(map_request: MapRequest):
    preview_payload = await asyncio.to_thread(_build_map_preview_payload, map_request)
    metadata = session_store.load_metadata(map_request.session_id)
    context = {
        "title": metadata["filename"],
        "map_payload_json": serialize_for_template(preview_payload.model_dump()),
        "summary_json": json.dumps(preview_payload.summary.model_dump(), ensure_ascii=False),
    }
    pdf_path = await build_pdf_file(templates.get_template("export_pdf.html"), context)
    filename = f"{sanitize_filename(metadata['filename'])}_{map_request.map_type}.pdf"
    return build_pdf_response(pdf_path, filename)
