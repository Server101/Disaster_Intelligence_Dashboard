from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.fema_data_service import load_fema_data

CURATED_DIR = ROOT_DIR / "data" / "curated"
SAMPLE_DIR = ROOT_DIR / "data" / "sample"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

DASHBOARD_FILE = CURATED_DIR / "fema_dashboard_dataset.csv"
DASHBOARD_SAMPLE_FILE = SAMPLE_DIR / "fema_dashboard_dataset_sample.csv"

print("Starting dashboard dataset creation...")
result = load_fema_data(ROOT_DIR, allow_remote=True)
dashboard_df = result.frame

if dashboard_df.empty:
    raise RuntimeError("The dashboard dataset is empty.")

sample_size = min(1000, len(dashboard_df))
if len(dashboard_df) > sample_size:
    step = len(dashboard_df) / sample_size
    sample_indexes = [int(index * step) for index in range(sample_size)]
    sample_df = dashboard_df.iloc[sample_indexes].copy()
else:
    sample_df = dashboard_df.copy()

if result.is_sample:
    if DASHBOARD_FILE.exists():
        DASHBOARD_FILE.unlink()
else:
    dashboard_df.to_csv(DASHBOARD_FILE, index=False)

sample_df.to_csv(DASHBOARD_SAMPLE_FILE, index=False)

print(f"Data source: {result.source_label}")
print(f"Sample mode: {result.is_sample}")
print(f"Dashboard rows prepared: {len(dashboard_df):,}")
print(f"Dashboard columns prepared: {len(dashboard_df.columns):,}")
if result.is_sample:
    print("A full dashboard file was not created because only sample data was available.")
else:
    print(f"Dashboard dataset saved to: {DASHBOARD_FILE}")
print(f"Dashboard sample saved to: {DASHBOARD_SAMPLE_FILE}")
print("Dashboard dataset creation complete.")
