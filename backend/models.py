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


class ForecastPoint(BaseModel):
    month: str
    record_type: str
    declaration_records: int
    lower_estimate: int | None = None
    upper_estimate: int | None = None


class ForecastResponse(BaseModel):
    region: str
    horizon: int = Field(ge=1, le=24)
    method: str
    generated_at: str
    points: list[ForecastPoint]
