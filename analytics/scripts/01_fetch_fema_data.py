import pandas as pd
from pathlib import Path

DATA_URL = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries.csv"

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
SAMPLE_DIR = BASE_DIR / "data" / "sample"

RAW_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

raw_file = RAW_DIR / "disaster_declarations_raw.csv"
sample_file = SAMPLE_DIR / "disaster_declarations_sample.csv"

print("Downloading FEMA Disaster Declarations dataset...")
df = pd.read_csv(DATA_URL)

print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns):,}")

df.to_csv(raw_file, index=False)

sample_df = df.head(1000)
sample_df.to_csv(sample_file, index=False)

print(f"Raw dataset saved locally to: {raw_file}")
print(f"Sample dataset saved to: {sample_file}")

print("\nDataset preview:")
print(df.head())

print("\nColumn names:")
print(df.columns.tolist())