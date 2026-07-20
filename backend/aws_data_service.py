from __future__ import annotations

import os
import time
from io import BytesIO
from pathlib import Path

import boto3
import pandas as pd

from backend.fema_data_service import DataLoadResult, load_fema_data, normalize_fema_data
from backend.forecast_service import generate_region_forecast


class AwsDataService:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.bucket_name = os.getenv("FEMA_S3_BUCKET", "").strip()
        self.dashboard_key = os.getenv(
            "FEMA_S3_DASHBOARD_KEY",
            "dashboard/fema_dashboard_dataset.csv",
        ).strip()
        self.forecast_key = os.getenv(
            "FEMA_S3_FORECAST_KEY",
            "forecasts/monthly_declaration_forecast.csv",
        ).strip()
        self.aws_region = os.getenv("AWS_REGION", "us-east-1").strip()
        self.cache_seconds = int(os.getenv("FEMA_DATA_CACHE_SECONDS", "21600"))
        self._s3 = boto3.client("s3", region_name=self.aws_region)
        self._dashboard_cache: DataLoadResult | None = None
        self._dashboard_cache_time = 0.0
        self._forecast_cache: dict[tuple[str, int, int], tuple[float, pd.DataFrame]] = {}

    def _cache_is_fresh(self, cached_at: float) -> bool:
        return time.monotonic() - cached_at < self.cache_seconds

    def _read_s3_csv(self, key: str) -> pd.DataFrame:
        response = self._s3.get_object(Bucket=self.bucket_name, Key=key)
        return pd.read_csv(BytesIO(response["Body"].read()), low_memory=False)

    def load_dashboard_data(self) -> DataLoadResult:
        if self._dashboard_cache and self._cache_is_fresh(self._dashboard_cache_time):
            return self._dashboard_cache

        result: DataLoadResult | None = None
        if self.bucket_name:
            try:
                frame = normalize_fema_data(self._read_s3_csv(self.dashboard_key))
                if not frame.empty:
                    result = DataLoadResult(
                        frame=frame,
                        source_label=f"Amazon S3: s3://{self.bucket_name}/{self.dashboard_key}",
                        is_sample=False,
                    )
            except Exception:
                result = None

        if result is None:
            result = load_fema_data(self.base_dir, allow_remote=True)

        self._dashboard_cache = result
        self._dashboard_cache_time = time.monotonic()
        return result

    def load_forecast_data(
        self,
        frame: pd.DataFrame,
        region: str,
        horizon: int,
        history_months: int = 60,
    ) -> pd.DataFrame:
        cache_key = (region, horizon, history_months)
        cached = self._forecast_cache.get(cache_key)
        if cached and self._cache_is_fresh(cached[0]):
            return cached[1].copy()

        combined: pd.DataFrame | None = None
        if self.bucket_name:
            try:
                stored = self._read_s3_csv(self.forecast_key)
                stored["month"] = pd.to_datetime(stored["month"], errors="coerce")
                regional = stored.loc[stored["region"] == region].copy()
                historical = regional.loc[regional["recordType"] == "Historical"].tail(
                    history_months
                )
                forecast = regional.loc[regional["recordType"] == "Forecast"].head(horizon)
                candidate = pd.concat([historical, forecast], ignore_index=True)
                if not candidate.empty and len(forecast) >= horizon:
                    combined = candidate
            except Exception:
                combined = None

        if combined is None:
            combined = generate_region_forecast(
                frame,
                region=region,
                horizon=horizon,
                history_months=history_months,
            )

        self._forecast_cache[cache_key] = (time.monotonic(), combined.copy())
        return combined
