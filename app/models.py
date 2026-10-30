from typing import Literal
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class CartographicMetadata(BaseModel):
    model_config = ConfigDict(strict=True, str_strip_whitespace=True)
    event: str = Field(min_length=2, max_length=100)
    geographic_unit: str = Field(min_length=2, max_length=100)
    period_start: str
    period_end: str
    author: str = Field(min_length=2, max_length=120)
    synthetic: Literal[True]
    period_confirmed: Literal[True]

    @model_validator(mode="after")
    def check_period(self):
        try:
            start, end = date.fromisoformat(self.period_start), date.fromisoformat(self.period_end)
        except ValueError:
            raise ValueError("Completa Desde y Hasta con fechas validas (AAAA-MM-DD).") from None
        if start > end:
            raise ValueError("La fecha inicial no puede ser posterior a la final.")
        return self


class MapRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: str
    lat_column: str = Field(min_length=1)
    lon_column: str = Field(min_length=1)
    map_type: Literal["points", "heatmap", "hotmap", "cluster", "category", "choropleth", "proportional", "profile"] = "points"
    cartographic_metadata: CartographicMetadata
    tile_layer: Literal[
        "OpenStreetMap",
        "Esri Light Gray",
        "Esri Dark Gray",
        "Esri World Imagery",
    ] = "OpenStreetMap"
    label_column: str | None = None
    category_column: str | None = None
    heat_radius: int = Field(default=25, ge=5, le=60)
    heat_palette: Literal["classic", "blues", "teal", "viridis", "grays"] = "classic"
    bandwidth_m: int = Field(default=500, ge=100, le=5000)
    heat_levels: list[int] = Field(default_factory=lambda: [10, 38, 58, 78, 100], min_length=5, max_length=5)
    distance_metric: Literal["manhattan", "euclidean"] = "manhattan"
    buffer_radius_m: int = Field(default=400, ge=50, le=5000)
    decay_exponent_out: float = Field(default=1.2, gt=0, le=6)
    decay_exponent_in: float = Field(default=2.0, gt=0, le=8)
    scale_constant: float = Field(default=1.0, gt=0, le=1000)
    known_anchor_lat: float | None = Field(default=None, ge=-90, le=90)
    known_anchor_lon: float | None = Field(default=None, ge=-180, le=180)
    personal_analysis: str | None = None

    @field_validator("tile_layer", mode="before")
    @classmethod
    def migrate_basemap(cls, value):
        return {"CartoDB Positron": "Esri Light Gray", "CartoDB DarkMatter": "Esri Dark Gray"}.get(value, value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_map_specific_fields(self) -> "MapRequest":
        if not (1 <= self.heat_levels[0] and self.heat_levels[-1] == 100
                and all(left < right for left, right in zip(self.heat_levels, self.heat_levels[1:]))):
            raise ValueError("Los niveles de calor deben ser crecientes entre 1 y 100; el ultimo debe ser 100.")
        if self.map_type == "category" and not self.category_column:
            raise ValueError("Debes seleccionar una columna de categoria para ese tipo de mapa.")
        if (self.known_anchor_lat is None) != (self.known_anchor_lon is None):
            raise ValueError("Debes informar ambas coordenadas del punto de anclaje conocido para calcular HS%.")
        return self


class MapSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    total_rows: int
    valid_rows: int
    invalid_rows: int
    invalid_breakdown: list[str]
    bounds: dict[str, float] | None
    detected_swap_warning: bool


class AnchorEstimate(BaseModel):
    model_config = ConfigDict(strict=True)

    lat: float
    lon: float
    score: float


class GeographicProfile(BaseModel):
    model_config = ConfigDict(strict=True)

    crimes_used: int
    grid_rows: int
    grid_cols: int
    projection_epsg: int
    distance_metric: Literal["manhattan", "euclidean"]
    buffer_radius_m: int
    decay_exponent_out: float
    decay_exponent_in: float
    scale_constant: float
    cell_size_m: float
    hit_score_percentage: float | None
    anchor_estimate: AnchorEstimate
    warnings: list[str]
    notes: list[str]
    systematic_analysis: list[str]
    jeopardy_points: list[list[float]]


class MapPreviewResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    session_id: str
    map_config: MapRequest
    summary: MapSummary
    points: list[dict]
    category_legend: list[dict[str, str]]
    popup_fields: list[str]
    profile: GeographicProfile | None = None
    cartography: dict
    density: dict | None = None
