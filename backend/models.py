from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    data_source: str
    sample_mode: bool
    declaration_records: int
    checked_at: datetime


class MetadataResponse(BaseModel):
    minimum_date: str
    maximum_date: str
    years: list[int]
    states: list[str]
    regions: list[str]
    incident_types: list[str]
    declaration_types: list[str]
    data_source: str
    sample_mode: bool


class SummaryResponse(BaseModel):
    declaration_records: int
    unique_disaster_numbers: int
    top_state: str
    top_incident_type: str
    peak_year: int


class TrendPoint(BaseModel):
    period: str
    declaration_records: int


class TrendResponse(BaseModel):
    grain: str
    points: list[TrendPoint]


class CategoryPoint(BaseModel):
    name: str
    declaration_records: int


class CategoryResponse(BaseModel):
    points: list[CategoryPoint]


class SeasonInsight(BaseModel):
    name: str
    declaration_records: int
    months: list[str]


class TrendInsight(BaseModel):
    direction: str
    prior_average: float
    recent_average: float
    percent_change: float
    interpretation: str
    limitation: str


class SpikeInsight(BaseModel):
    year: int
    declaration_records: int
    top_incident_type: str
    top_incident_records: int
    explanation: str
    limitation: str


class RecordComparisonInsight(BaseModel):
    declaration_records: int
    unique_disaster_numbers: int
    records_per_disaster: float
    interpretation: str
    limitation: str


class InsightsResponse(BaseModel):
    top_month: CategoryPoint
    top_season: SeasonInsight
    top_states: list[CategoryPoint]
    top_incident_types: list[CategoryPoint]
    top_regions: list[CategoryPoint]
    long_term_trend: TrendInsight
    historical_spikes: list[SpikeInsight]
    records_vs_disasters: RecordComparisonInsight


class ForecastPoint(BaseModel):
    month: str
    record_type: str
    declaration_records: int
    lower_estimate: int | None = None
    upper_estimate: int | None = None
    likely_incident_type: str | None = None
    incident_type_support: float | None = None
    incident_type_confidence: str | None = None
    likely_areas: str | None = None


class ForecastResponse(BaseModel):
    region: str
    horizon: int = Field(ge=1, le=24)
    method: str
    type_method: str | None = None
    type_limitation: str | None = None
    generated_at: str
    as_of_date: str | None = None
    training_through: str | None = None
    forecast_start: str | None = None
    validation_mae: float | None = None
    points: list[ForecastPoint]
