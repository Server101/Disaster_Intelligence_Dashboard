from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

FORECAST_METHOD = (
    "Backtested monthly forecasting with seasonal-trend regression and "
    "a seasonal-naive benchmark"
)
SEASON_LENGTH = 12
MAX_TRAINING_MONTHS = 180
VALIDATION_MONTHS = 12


def _month_start(value: date | datetime | pd.Timestamp | None = None) -> pd.Timestamp:
    if value is None:
        timestamp = pd.Timestamp.now(tz="UTC").tz_localize(None)
    else:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return timestamp.to_period("M").to_timestamp()


def _forecast_start(as_of: date | datetime | pd.Timestamp | None = None) -> pd.Timestamp:
    return _month_start(as_of) + pd.offsets.MonthBegin(1)


def _monthly_counts(
    frame: pd.DataFrame,
    region: str,
    as_of: date | datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    required_columns = {"declarationDate", "femaRegion"}
    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"Forecast data is missing required columns: {missing_text}")

    current_month = _month_start(as_of)
    regional = frame.loc[
        (frame["femaRegion"] == region) & frame["declarationDate"].notna(),
        ["declarationDate"],
    ].copy()

    if regional.empty:
        raise ValueError(f"No declaration records are available for {region}.")

    regional["declarationDate"] = pd.to_datetime(
        regional["declarationDate"],
        errors="coerce",
        utc=True,
    ).dt.tz_convert(None)
    regional = regional.loc[regional["declarationDate"] < current_month]
    regional["month"] = regional["declarationDate"].dt.to_period("M").dt.to_timestamp()
    regional = regional.dropna(subset=["month"])

    if regional.empty:
        raise ValueError(f"No completed monthly history is available for {region}.")

    counts = regional.groupby("month").size().rename("declarationRecords")
    last_observed_month = min(counts.index.max(), current_month - pd.offsets.MonthBegin(1))
    month_index = pd.date_range(counts.index.min(), last_observed_month, freq="MS")
    history = counts.reindex(month_index, fill_value=0).rename_axis("month").reset_index()
    history["declarationRecords"] = history["declarationRecords"].astype(float)
    return history


def _month_offsets(months: pd.Series | pd.DatetimeIndex, origin: pd.Timestamp) -> np.ndarray:
    month_index = pd.DatetimeIndex(months)
    return np.asarray(
        (month_index.year - origin.year) * 12 + (month_index.month - origin.month),
        dtype=float,
    )


def _design_matrix(months: pd.Series | pd.DatetimeIndex, origin: pd.Timestamp) -> np.ndarray:
    month_index = pd.DatetimeIndex(months)
    offsets = _month_offsets(month_index, origin)
    trend_years = offsets / 12.0
    columns = [np.ones(len(month_index)), trend_years]

    month_position = month_index.month.to_numpy(dtype=float) - 1.0
    for harmonic in range(1, 4):
        angle = 2.0 * np.pi * harmonic * month_position / SEASON_LENGTH
        columns.extend([np.sin(angle), np.cos(angle)])

    return np.column_stack(columns)


def _fit_regression(history: pd.DataFrame) -> tuple[np.ndarray, pd.Timestamp]:
    training = history.tail(MAX_TRAINING_MONTHS).copy()
    origin = pd.Timestamp(training["month"].iloc[0])
    design = _design_matrix(training["month"], origin)
    target = np.log1p(training["declarationRecords"].to_numpy(dtype=float))

    offsets = _month_offsets(training["month"], origin)
    recency = offsets.max() - offsets
    weights = np.power(0.5, recency / 36.0)

    weighted_design = design * weights[:, None]
    penalty = np.eye(design.shape[1]) * 0.12
    penalty[0, 0] = 0.0
    coefficients = np.linalg.pinv(design.T @ weighted_design + penalty) @ (
        design.T @ (weights * target)
    )
    return coefficients, origin


def _regression_predictions(
    history: pd.DataFrame,
    future_months: pd.DatetimeIndex,
) -> np.ndarray:
    coefficients, origin = _fit_regression(history)
    transformed = _design_matrix(future_months, origin) @ coefficients
    return np.maximum(0.0, np.expm1(transformed))


def _level_adjustment(history: pd.DataFrame) -> float:
    values = history["declarationRecords"]
    if len(values) < 24:
        return 1.0

    recent_average = values.tail(12).mean()
    previous_average = values.iloc[-24:-12].mean()
    if previous_average <= 0:
        return 1.0

    return float(np.clip(recent_average / previous_average, 0.65, 1.35))


def _seasonal_naive_predictions(
    history: pd.DataFrame,
    future_months: pd.DatetimeIndex,
) -> np.ndarray:
    level_adjustment = _level_adjustment(history)
    predictions: list[float] = []

    for forecast_month in future_months:
        same_month = history.loc[
            history["month"].dt.month == forecast_month.month,
            "declarationRecords",
        ].tail(5)
        if same_month.empty:
            base_value = float(history["declarationRecords"].tail(12).mean())
        else:
            weights = np.arange(1, len(same_month) + 1, dtype=float)
            base_value = float(np.average(same_month.to_numpy(dtype=float), weights=weights))
        predictions.append(max(0.0, base_value * level_adjustment))

    return np.asarray(predictions, dtype=float)


def _mean_absolute_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    if len(actual) == 0:
        return float("nan")
    return float(np.mean(np.abs(actual - predicted)))


def _select_model(history: pd.DataFrame) -> tuple[str, float | None]:
    training = history.tail(MAX_TRAINING_MONTHS).copy()
    if len(training) < 48:
        return "seasonal-trend regression", None

    model_training = training.iloc[:-VALIDATION_MONTHS].copy()
    validation = training.iloc[-VALIDATION_MONTHS:].copy()
    actual = validation["declarationRecords"].to_numpy(dtype=float)

    regression = _regression_predictions(
        model_training,
        pd.DatetimeIndex(validation["month"]),
    )
    seasonal_naive = _seasonal_naive_predictions(
        model_training,
        pd.DatetimeIndex(validation["month"]),
    )
    regression_mae = _mean_absolute_error(actual, regression)
    seasonal_mae = _mean_absolute_error(actual, seasonal_naive)

    if seasonal_mae < regression_mae:
        return "seasonal-naive benchmark", seasonal_mae
    return "seasonal-trend regression", regression_mae


def _residual_scale(history: pd.DataFrame, model_name: str) -> float:
    training = history.tail(MAX_TRAINING_MONTHS).copy()
    actual = training["declarationRecords"].to_numpy(dtype=float)

    if model_name == "seasonal-naive benchmark" and len(training) > SEASON_LENGTH:
        fitted = training["declarationRecords"].shift(SEASON_LENGTH).to_numpy(dtype=float)
        residuals = actual[SEASON_LENGTH:] - fitted[SEASON_LENGTH:]
    else:
        fitted = _regression_predictions(training, pd.DatetimeIndex(training["month"]))
        residuals = actual - fitted

    residuals = residuals[np.isfinite(residuals)]
    if len(residuals) == 0:
        return 1.0

    median = float(np.median(residuals))
    mad_scale = float(np.median(np.abs(residuals - median)) * 1.4826)
    rmse_scale = float(np.sqrt(np.mean(np.square(residuals))))
    return max(1.0, mad_scale, rmse_scale * 0.65)


def generate_region_forecast(
    frame: pd.DataFrame,
    region: str,
    horizon: int = 12,
    history_months: int = 60,
    as_of: date | datetime | pd.Timestamp | None = None,
) -> pd.DataFrame:
    if horizon < 1 or horizon > 24:
        raise ValueError("Forecast horizon must be between 1 and 24 months.")
    if history_months < 12:
        raise ValueError("History display must include at least 12 months.")

    history = _monthly_counts(frame, region, as_of=as_of)
    first_forecast_month = _forecast_start(as_of)
    future_months = pd.date_range(first_forecast_month, periods=horizon, freq="MS")
    model_name, validation_mae = _select_model(history)

    if model_name == "seasonal-naive benchmark":
        estimates = _seasonal_naive_predictions(history, future_months)
    else:
        estimates = _regression_predictions(history, future_months)

    residual_scale = _residual_scale(history, model_name)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    as_of_date = pd.Timestamp(as_of or datetime.now(timezone.utc)).date().isoformat()
    training_through = pd.Timestamp(history["month"].max()).strftime("%Y-%m")
    forecast_start = first_forecast_month.strftime("%Y-%m")

    displayed_history = history.tail(history_months).copy()
    displayed_history["region"] = region
    displayed_history["recordType"] = "Historical"
    displayed_history["lowerEstimate"] = pd.NA
    displayed_history["upperEstimate"] = pd.NA

    forecast_rows = []
    for step, (forecast_month, estimate) in enumerate(zip(future_months, estimates), start=1):
        uncertainty = 1.28 * residual_scale * np.sqrt(1.0 + step / 12.0)
        forecast_rows.append(
            {
                "month": forecast_month,
                "region": region,
                "recordType": "Forecast",
                "declarationRecords": round(max(0.0, estimate)),
                "lowerEstimate": round(max(0.0, estimate - uncertainty)),
                "upperEstimate": round(max(0.0, estimate + uncertainty)),
            }
        )

    forecast = pd.DataFrame(forecast_rows)
    combined = pd.concat([displayed_history, forecast], ignore_index=True)
    combined["declarationRecords"] = combined["declarationRecords"].round().astype("Int64")
    combined["lowerEstimate"] = combined["lowerEstimate"].astype("Int64")
    combined["upperEstimate"] = combined["upperEstimate"].astype("Int64")

    validation_text = (
        f"; 12-month holdout MAE {validation_mae:.1f} records"
        if validation_mae is not None
        else "; limited-history validation"
    )
    combined["method"] = f"Backtested {model_name}{validation_text}"
    combined["generatedAt"] = generated_at
    combined["asOfDate"] = as_of_date
    combined["trainingThrough"] = training_through
    combined["forecastStart"] = forecast_start
    combined["validationMae"] = validation_mae

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
            "asOfDate",
            "trainingThrough",
            "forecastStart",
            "validationMae",
        ]
    ]


def generate_all_region_forecasts(
    frame: pd.DataFrame,
    horizon: int = 12,
    history_months: int = 60,
    as_of: date | datetime | pd.Timestamp | None = None,
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
            as_of=as_of,
        )
        for region in regions
        if region != "Not Reported"
    ]

    if not forecasts:
        raise ValueError("No FEMA regions are available for forecasting.")

    return pd.concat(forecasts, ignore_index=True)
