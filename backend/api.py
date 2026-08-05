from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.aws_data_service import AwsDataService
from backend.fema_data_service import apply_filters, sort_region_labels
from backend.models import (
    CategoryPoint,
    CategoryResponse,
    ForecastPoint,
    ForecastResponse,
    HealthResponse,
    InsightsResponse,
    MetadataResponse,
    RecordComparisonInsight,
    SeasonInsight,
    SpikeInsight,
    SummaryResponse,
    TrendInsight,
    TrendPoint,
    TrendResponse,
)

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_SERVICE = AwsDataService(ROOT_DIR)

app = FastAPI(
    title="FEMA Disaster Intelligence API",
    version="1.0.0",
    description="Summary, trend, regional, incident-type, and forecast data for the FEMA Disaster Intelligence project.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

allowed_origins = [
    value.strip()
    for value in os.getenv(
        "FEMA_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:8501,https://disaster-intelligence-dashboard.streamlit.app",
    ).split(",")
    if value.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _load_data():
    try:
        return DATA_SERVICE.load_dashboard_data()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _filtered_data(
    frame: pd.DataFrame,
    start_date: date | None,
    end_date: date | None,
    state: str | None,
    region: str | None,
    incident_type: str | None,
    declaration_type: str | None,
) -> pd.DataFrame:
    available_dates = frame["declarationDate"].dropna()
    if available_dates.empty:
        raise HTTPException(status_code=503, detail="No usable declaration dates are available.")

    resolved_start = start_date or available_dates.min().date()
    resolved_end = end_date or available_dates.max().date()
    if resolved_start > resolved_end:
        raise HTTPException(status_code=400, detail="The start date must not be after the end date.")

    return apply_filters(
        frame,
        resolved_start,
        resolved_end,
        [state] if state else [],
        [region] if region else [],
        [incident_type] if incident_type else [],
        [declaration_type] if declaration_type else [],
    )


@app.get("/", include_in_schema=False)
@app.get("/api", include_in_schema=False)
def root():
    return {"name": "FEMA Disaster Intelligence API", "docs": "/api/docs"}


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse, include_in_schema=False)
def health():
    result = _load_data()
    return HealthResponse(
        status="ok",
        data_source=result.source_label,
        sample_mode=result.is_sample,
        declaration_records=len(result.frame),
        checked_at=datetime.now(timezone.utc),
    )


@app.get("/metadata", response_model=MetadataResponse)
@app.get("/api/metadata", response_model=MetadataResponse, include_in_schema=False)
def metadata():
    result = _load_data()
    frame = result.frame
    available_dates = frame["declarationDate"].dropna()
    if available_dates.empty:
        raise HTTPException(status_code=503, detail="No usable declaration dates are available.")

    years = sorted(
        int(value)
        for value in frame["declarationYear"].dropna().unique().tolist()
    )
    return MetadataResponse(
        minimum_date=available_dates.min().date().isoformat(),
        maximum_date=available_dates.max().date().isoformat(),
        years=years,
        states=sorted(frame["state"].dropna().unique().tolist()),
        regions=[
            region
            for region in sort_region_labels(frame["femaRegion"].dropna().unique().tolist())
            if region != "Not Reported"
        ],
        incident_types=sorted(frame["incidentType"].dropna().unique().tolist()),
        declaration_types=sorted(
            frame["declarationTypeLabel"].dropna().unique().tolist()
        ),
        data_source=result.source_label,
        sample_mode=result.is_sample,
    )


@app.get("/summary", response_model=SummaryResponse)
@app.get("/api/summary", response_model=SummaryResponse, include_in_schema=False)
def summary(
    start_date: date | None = None,
    end_date: date | None = None,
    state: str | None = None,
    region: str | None = None,
    incident_type: str | None = None,
    declaration_type: str | None = None,
):
    result = _load_data()
    filtered = _filtered_data(
        result.frame,
        start_date,
        end_date,
        state,
        region,
        incident_type,
        declaration_type,
    )
    if filtered.empty:
        raise HTTPException(status_code=404, detail="No declaration records match the filters.")

    return SummaryResponse(
        declaration_records=len(filtered),
        unique_disaster_numbers=int(filtered["disasterNumber"].nunique(dropna=True)),
        top_state=str(filtered["state"].value_counts().idxmax()),
        top_incident_type=str(filtered["incidentType"].value_counts().idxmax()),
        peak_year=int(filtered["declarationYear"].value_counts().idxmax()),
    )


@app.get("/trends", response_model=TrendResponse)
@app.get("/api/trends", response_model=TrendResponse, include_in_schema=False)
def trends(
    grain: str = Query("year", pattern="^(year|month)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    region: str | None = None,
):
    result = _load_data()
    frame = _filtered_data(
        result.frame,
        start_date,
        end_date,
        None,
        region,
        None,
        None,
    )
    if frame.empty:
        raise HTTPException(status_code=404, detail="No declaration records match the filters.")

    if grain == "month":
        grouped = (
            frame.dropna(subset=["declarationMonthYear"])
            .groupby("declarationMonthYear")
            .size()
            .sort_index()
        )
    else:
        grouped = (
            frame.dropna(subset=["declarationYear"])
            .groupby("declarationYear")
            .size()
            .sort_index()
        )

    points = [
        TrendPoint(period=str(period), declaration_records=int(count))
        for period, count in grouped.items()
    ]
    return TrendResponse(grain=grain, points=points)


@app.get("/regions", response_model=CategoryResponse)
@app.get("/api/regions", response_model=CategoryResponse, include_in_schema=False)
def regions(
    start_date: date | None = None,
    end_date: date | None = None,
):
    result = _load_data()
    frame = _filtered_data(
        result.frame,
        start_date,
        end_date,
        None,
        None,
        None,
        None,
    )
    counts = frame["femaRegion"].value_counts()
    ordered_regions = sort_region_labels(counts.index.tolist())
    points = [
        CategoryPoint(name=region, declaration_records=int(counts.get(region, 0)))
        for region in ordered_regions
        if region != "Not Reported"
    ]
    return CategoryResponse(points=points)


@app.get("/incident-types", response_model=CategoryResponse)
@app.get("/api/incident-types", response_model=CategoryResponse, include_in_schema=False)
def incident_types(
    limit: int = Query(10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    region: str | None = None,
):
    result = _load_data()
    frame = _filtered_data(
        result.frame,
        start_date,
        end_date,
        None,
        region,
        None,
        None,
    )
    counts = frame["incidentType"].value_counts().head(limit)
    points = [
        CategoryPoint(name=str(name), declaration_records=int(count))
        for name, count in counts.items()
    ]
    return CategoryResponse(points=points)


@app.get("/states", response_model=CategoryResponse)
@app.get("/api/states", response_model=CategoryResponse, include_in_schema=False)
def states(
    limit: int = Query(10, ge=1, le=50),
    start_date: date | None = None,
    end_date: date | None = None,
    region: str | None = None,
):
    result = _load_data()
    frame = _filtered_data(
        result.frame,
        start_date,
        end_date,
        None,
        region,
        None,
        None,
    )
    counts = frame["state"].value_counts().head(limit)
    points = [
        CategoryPoint(name=str(name), declaration_records=int(count))
        for name, count in counts.items()
    ]
    return CategoryResponse(points=points)


@app.get("/seasonality", response_model=CategoryResponse)
@app.get("/api/seasonality", response_model=CategoryResponse, include_in_schema=False)
def seasonality(
    start_date: date | None = None,
    end_date: date | None = None,
    region: str | None = None,
):
    result = _load_data()
    frame = _filtered_data(
        result.frame,
        start_date,
        end_date,
        None,
        region,
        None,
        None,
    )
    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    counts = frame["declarationMonthName"].value_counts()
    points = [
        CategoryPoint(name=month, declaration_records=int(counts.get(month, 0)))
        for month in month_order
    ]
    return CategoryResponse(points=points)


@app.get("/insights", response_model=InsightsResponse)
@app.get("/api/insights", response_model=InsightsResponse, include_in_schema=False)
def insights(
    start_date: date | None = None,
    end_date: date | None = None,
    region: str | None = None,
):
    result = _load_data()
    frame = _filtered_data(
        result.frame,
        start_date,
        end_date,
        None,
        region,
        None,
        None,
    )
    if frame.empty:
        raise HTTPException(status_code=404, detail="No declaration records match the filters.")

    month_counts = frame["declarationMonthName"].value_counts()
    top_month_name = str(month_counts.idxmax())
    top_month = CategoryPoint(
        name=top_month_name,
        declaration_records=int(month_counts.loc[top_month_name]),
    )

    seasons = {
        "Winter": ["December", "January", "February"],
        "Spring": ["March", "April", "May"],
        "Summer": ["June", "July", "August"],
        "Fall": ["September", "October", "November"],
    }
    season_counts = {
        season: int(month_counts.reindex(months, fill_value=0).sum())
        for season, months in seasons.items()
    }
    top_season_name = max(season_counts, key=season_counts.get)
    top_season = SeasonInsight(
        name=top_season_name,
        declaration_records=season_counts[top_season_name],
        months=seasons[top_season_name],
    )

    def top_points(column: str, limit: int = 5) -> list[CategoryPoint]:
        counts = frame[column].value_counts().head(limit)
        return [
            CategoryPoint(name=str(name), declaration_records=int(count))
            for name, count in counts.items()
            if str(name) != "Not Reported"
        ]

    yearly = (
        frame.dropna(subset=["declarationYear"])
        .groupby("declarationYear")
        .size()
        .sort_index()
    )
    current_year = datetime.now(timezone.utc).year
    complete_yearly = yearly.loc[yearly.index < current_year]
    if len(complete_yearly) < 4:
        complete_yearly = yearly

    window = min(10, max(2, len(complete_yearly) // 2))
    recent_values = complete_yearly.tail(window)
    prior_values = complete_yearly.iloc[-2 * window : -window]
    if prior_values.empty:
        split = max(1, len(complete_yearly) // 2)
        prior_values = complete_yearly.iloc[:split]
        recent_values = complete_yearly.iloc[split:]

    prior_average = float(prior_values.mean()) if not prior_values.empty else 0.0
    recent_average = float(recent_values.mean()) if not recent_values.empty else 0.0
    percent_change = (
        ((recent_average - prior_average) / prior_average) * 100.0
        if prior_average > 0
        else 0.0
    )
    if percent_change > 5:
        direction = "increasing"
    elif percent_change < -5:
        direction = "decreasing"
    else:
        direction = "relatively stable"
    interpretation = (
        f"The average annual declaration-record total is {abs(percent_change):.1f}% "
        f"{'higher' if percent_change >= 0 else 'lower'} in the most recent "
        f"{len(recent_values)} complete years than in the preceding comparison period. "
        f"This indicates an {direction} long-term administrative record pattern." if direction == "increasing" else f"This indicates a {direction} long-term administrative record pattern."
    )
    trend_insight = TrendInsight(
        direction=direction,
        prior_average=round(prior_average, 1),
        recent_average=round(recent_average, 1),
        percent_change=round(percent_change, 1),
        interpretation=interpretation,
        limitation=(
            "Annual declaration-record totals are affected by event scale, designated-area "
            "reporting, policy, and incomplete recent years; they are not a severity index."
        ),
    )

    spike_years = complete_yearly.nlargest(3)
    spike_insights: list[SpikeInsight] = []
    for year_value, record_count in spike_years.items():
        year = int(year_value)
        year_frame = frame.loc[frame["declarationYear"] == year]
        incident_counts = year_frame["incidentType"].value_counts()
        top_incident = str(incident_counts.idxmax())
        top_incident_records = int(incident_counts.loc[top_incident])
        share = (top_incident_records / int(record_count)) * 100.0
        spike_insights.append(
            SpikeInsight(
                year=year,
                declaration_records=int(record_count),
                top_incident_type=top_incident,
                top_incident_records=top_incident_records,
                explanation=(
                    f"{year} contains {int(record_count):,} declaration records. "
                    f"{top_incident} is the leading category with "
                    f"{top_incident_records:,} records ({share:.1f}% of that year), "
                    "showing which incident classification contributes most to the spike."
                ),
                limitation=(
                    "This identifies an association inside the FEMA records, not a single "
                    "causal event. One disaster can create multiple designated-area rows."
                ),
            )
        )

    declaration_records = len(frame)
    unique_disasters = int(frame["disasterNumber"].nunique(dropna=True))
    records_per_disaster = (
        declaration_records / unique_disasters if unique_disasters else 0.0
    )
    records_comparison = RecordComparisonInsight(
        declaration_records=declaration_records,
        unique_disaster_numbers=unique_disasters,
        records_per_disaster=round(records_per_disaster, 2),
        interpretation=(
            f"The selected data contains {declaration_records:,} administrative records "
            f"for {unique_disasters:,} distinct disaster numbers, or about "
            f"{records_per_disaster:.2f} records per disaster number. The larger record "
            "count reflects separate designated areas and declaration details."
        ),
        limitation=(
            "The ratio varies by disaster scope and reporting structure. It should not be "
            "used to compare disaster severity or economic impact."
        ),
    )

    return InsightsResponse(
        top_month=top_month,
        top_season=top_season,
        top_states=top_points("state"),
        top_incident_types=top_points("incidentType"),
        top_regions=top_points("femaRegion"),
        long_term_trend=trend_insight,
        historical_spikes=spike_insights,
        records_vs_disasters=records_comparison,
    )


@app.get("/forecast", response_model=ForecastResponse)
@app.get("/api/forecast", response_model=ForecastResponse, include_in_schema=False)
def forecast(
    region: str = Query("Region 4"),
    horizon: int = Query(12, ge=6, le=12),
):
    result = _load_data()
    available_regions = set(result.frame["femaRegion"].dropna().unique().tolist())
    if region not in available_regions:
        raise HTTPException(status_code=404, detail=f"Forecast region not found: {region}")

    try:
        forecast_frame = DATA_SERVICE.load_forecast_data(
            result.frame,
            region=region,
            horizon=horizon,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    method = str(forecast_frame["method"].dropna().iloc[0])
    generated_at = str(forecast_frame["generatedAt"].dropna().iloc[0])
    as_of_date = (
        str(forecast_frame["asOfDate"].dropna().iloc[0])
        if "asOfDate" in forecast_frame.columns and forecast_frame["asOfDate"].notna().any()
        else None
    )
    training_through = (
        str(forecast_frame["trainingThrough"].dropna().iloc[0])
        if "trainingThrough" in forecast_frame.columns
        and forecast_frame["trainingThrough"].notna().any()
        else None
    )
    forecast_start = (
        str(forecast_frame["forecastStart"].dropna().iloc[0])
        if "forecastStart" in forecast_frame.columns
        and forecast_frame["forecastStart"].notna().any()
        else None
    )
    validation_mae = (
        float(forecast_frame["validationMae"].dropna().iloc[0])
        if "validationMae" in forecast_frame.columns
        and forecast_frame["validationMae"].notna().any()
        else None
    )
    points = []
    for row in forecast_frame.itertuples(index=False):
        points.append(
            ForecastPoint(
                month=pd.Timestamp(row.month).strftime("%Y-%m"),
                record_type=str(row.recordType),
                declaration_records=int(row.declarationRecords),
                lower_estimate=int(row.lowerEstimate)
                if pd.notna(row.lowerEstimate)
                else None,
                upper_estimate=int(row.upperEstimate)
                if pd.notna(row.upperEstimate)
                else None,
            )
        )

    return ForecastResponse(
        region=region,
        horizon=horizon,
        method=method,
        generated_at=generated_at,
        as_of_date=as_of_date,
        training_through=training_through,
        forecast_start=forecast_start,
        validation_mae=validation_mae,
        points=points,
    )
