from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

FORECAST_METHOD = "Seasonal moving average with recent-level adjustment"


def _monthly_counts(frame: pd.DataFrame, region: str) -> pd.DataFrame:
    required_columns = {"declarationDate", "femaRegion"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Forecast data is missing required columns: {missing_text}")

    regional = frame.loc[
        (frame["femaRegion"] == region) & frame["declarationDate"].notna(),
        ["declarationDate"],
    ].copy()

    if regional.empty:
        raise ValueError(f"No declaration records are available for {region}.")

    regional["month"] = (
        pd.to_datetime(regional["declarationDate"], errors="coerce")
        .dt.to_period("M")
        .dt.to_timestamp()
    )
    regional = regional.dropna(subset=["month"])

    counts = regional.groupby("month").size().rename("declarationRecords")
    month_index = pd.date_range(counts.index.min(), counts.index.max(), freq="MS")
    history = counts.reindex(month_index, fill_value=0).rename_axis("month").reset_index()
    history["declarationRecords"] = history["declarationRecords"].astype(float)
    return history


def _level_adjustment(history: pd.DataFrame) -> float:
    values = history["declarationRecords"]
    if len(values) < 24:
        return 1.0

    recent_average = values.tail(12).mean()
    previous_average = values.iloc[-24:-12].mean()
    if previous_average <= 0:
        return 1.0

    return float(np.clip(recent_average / previous_average, 0.75, 1.25))


def _forecast_value(
    history: pd.DataFrame,
    forecast_month: pd.Timestamp,
    level_adjustment: float,
) -> tuple[float, float]:
    month_number = forecast_month.month
    same_month = history.loc[
        history["month"].dt.month == month_number,
        "declarationRecords",
    ].tail(5)

    if len(same_month) >= 2:
        base_value = float(same_month.mean())
        spread = float(same_month.std(ddof=0))
    else:
        recent_window = history["declarationRecords"].tail(12)
        base_value = float(recent_window.mean())
        spread = float(recent_window.std(ddof=0))

    estimate = max(0.0, base_value * level_adjustment)
    uncertainty = max(spread, np.sqrt(max(estimate, 1.0)))
    return estimate, uncertainty


def generate_region_forecast(
    frame: pd.DataFrame,
    region: str,
    horizon: int = 12,
    history_months: int = 60,
) -> pd.DataFrame:
    if horizon < 1 or horizon > 24:
        raise ValueError("Forecast horizon must be between 1 and 24 months.")
    if history_months < 12:
        raise ValueError("History display must include at least 12 months.")

    history = _monthly_counts(frame, region)
    level_adjustment = _level_adjustment(history)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    displayed_history = history.tail(history_months).copy()
    displayed_history["region"] = region
    displayed_history["recordType"] = "Historical"
    displayed_history["lowerEstimate"] = pd.NA
    displayed_history["upperEstimate"] = pd.NA

    future_months = pd.date_range(
        history["month"].max() + pd.offsets.MonthBegin(1),
        periods=horizon,
        freq="MS",
    )

    forecast_rows = []
    for forecast_month in future_months:
        estimate, uncertainty = _forecast_value(
            history,
            forecast_month,
            level_adjustment,
        )
        forecast_rows.append(
            {
                "month": forecast_month,
                "region": region,
                "recordType": "Forecast",
                "declarationRecords": round(estimate),
                "lowerEstimate": round(max(0.0, estimate - uncertainty)),
                "upperEstimate": round(estimate + uncertainty),
            }
        )

    forecast = pd.DataFrame(forecast_rows)
    combined = pd.concat([displayed_history, forecast], ignore_index=True)
    combined["declarationRecords"] = combined["declarationRecords"].round().astype("Int64")
    combined["lowerEstimate"] = combined["lowerEstimate"].astype("Int64")
    combined["upperEstimate"] = combined["upperEstimate"].astype("Int64")
    combined["method"] = FORECAST_METHOD
    combined["generatedAt"] = generated_at
    return combined[
        [
            "region",
            "month",
            "recordType",
            "declarationRecords",
            "lowerEstimate",
            "upperEstimate",
            "method",
            "generatedAt",
        ]
    ]


def generate_all_region_forecasts(
    frame: pd.DataFrame,
    horizon: int = 12,
    history_months: int = 60,
) -> pd.DataFrame:
    regions = sorted(
        frame["femaRegion"].dropna().unique().tolist(),
        key=lambda label: int(label.split(" ", 1)[1])
        if isinstance(label, str) and label.startswith("Region ")
        else 999,
    )

    forecasts = [
        generate_region_forecast(
            frame,
            region=region,
            horizon=horizon,
            history_months=history_months,
        )
        for region in regions
        if region != "Not Reported"
    ]

    if not forecasts:
        raise ValueError("No FEMA regions are available for forecasting.")

    return pd.concat(forecasts, ignore_index=True)
