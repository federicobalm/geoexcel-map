from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UploadSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: str
    filename: str
    row_count: int
    column_count: int
    columns: list[str]
    preview_rows: list[dict[str, str]]
    suggested_lat_column: str | None
    suggested_lon_column: str | None
    candidate_category_columns: list[str]
    candidate_label_columns: list[str]
    notes: list[str]


class MapRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: str
    lat_column: str = Field(min_length=1)
    lon_column: str = Field(min_length=1)
    map_type: Literal["points", "heatmap", "cluster", "category"] = "points"
    tile_layer: Literal[
        "OpenStreetMap",
        "CartoDB Positron",
        "CartoDB DarkMatter",
        "Esri World Imagery",
    ] = "OpenStreetMap"
    label_column: str | None = None
    category_column: str | None = None
    heat_radius: int = Field(default=25, ge=5, le=60)


class MapSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    total_rows: int
    valid_rows: int
    invalid_rows: int
    invalid_breakdown: list[str]
    bounds: dict[str, float] | None
    detected_swap_warning: bool


class MapPreviewResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: str
    map_config: MapRequest
    summary: MapSummary
    points: list[dict]
    category_legend: list[dict[str, str]]
    popup_fields: list[str]
