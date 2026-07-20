from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.fema_data_service import load_fema_data
from backend.forecast_service import generate_all_region_forecasts

CURATED_DIR = ROOT_DIR / "data" / "curated"
SAMPLE_DIR = ROOT_DIR / "data" / "sample"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

FORECAST_FILE = CURATED_DIR / "monthly_declaration_forecast.csv"
FORECAST_SAMPLE_FILE = SAMPLE_DIR / "monthly_declaration_forecast_sample.csv"

print("Starting FEMA regional declaration-record forecasting...")
result = load_fema_data(ROOT_DIR, allow_remote=True)
forecast_df = generate_all_region_forecasts(
    result.frame,
    horizon=12,
    history_months=60,
)

forecast_df.to_csv(FORECAST_FILE, index=False)

forecast_only = forecast_df.loc[forecast_df["recordType"] == "Forecast"].copy()
forecast_sample = forecast_only.groupby("region", group_keys=False).head(12)
forecast_sample.to_csv(FORECAST_SAMPLE_FILE, index=False)

print(f"Data source: {result.source_label}")
print(f"Sample mode: {result.is_sample}")
print(f"Regions forecasted: {forecast_df['region'].nunique():,}")
print(f"Forecast rows created: {len(forecast_only):,}")
print(f"Forecast output saved to: {FORECAST_FILE}")
print(f"Forecast sample saved to: {FORECAST_SAMPLE_FILE}")
print("Forecasting complete.")
