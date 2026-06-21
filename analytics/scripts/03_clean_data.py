import pandas as pd
from pathlib import Path

print("Starting FEMA data cleaning...")

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_FILE = BASE_DIR / "data" / "raw" / "disaster_declarations_raw.csv"
CLEAN_DIR = BASE_DIR / "data" / "cleaned"
SAMPLE_DIR = BASE_DIR / "data" / "sample"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

CLEAN_FILE = CLEAN_DIR / "disaster_declarations_cleaned.csv"
CLEAN_SAMPLE_FILE = SAMPLE_DIR / "disaster_declarations_cleaned_sample.csv"

if not RAW_FILE.exists():
    raise FileNotFoundError(
        f"Raw data file not found: {RAW_FILE}\n"
        "Run analytics/scripts/01_fetch_fema_data.py first."
    )

df = pd.read_csv(RAW_FILE)

print(f"Raw rows loaded: {len(df):,}")
print(f"Raw columns loaded: {len(df.columns):,}")

# Standardize date fields
date_columns = [
    "declarationDate",
    "incidentBeginDate",
    "incidentEndDate",
    "disasterCloseoutDate",
    "lastIAFilingDate",
    "lastRefresh",
]

for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# Clean text fields
text_columns = [
    "state",
    "declarationType",
    "incidentType",
    "declarationTitle",
    "designatedArea",
]

for col in text_columns:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

# Standardize important columns
if "state" in df.columns:
    df["state"] = df["state"].str.upper()

if "incidentType" in df.columns:
    df["incidentType"] = df["incidentType"].str.title()

if "designatedArea" in df.columns:
    df["designatedArea"] = df["designatedArea"].str.title()

# Create derived date fields from declarationDate
if "declarationDate" in df.columns:
    df["declarationYear"] = df["declarationDate"].dt.year
    df["declarationMonth"] = df["declarationDate"].dt.month
    df["declarationMonthName"] = df["declarationDate"].dt.month_name()
    df["declarationQuarter"] = df["declarationDate"].dt.quarter
    df["declarationMonthYear"] = df["declarationDate"].dt.to_period("M").astype(str)

# Create FEMA region label
if "region" in df.columns:
    df["femaRegion"] = "Region " + df["region"].astype(str)

# Remove exact duplicate rows
before_dedup = len(df)
df = df.drop_duplicates()
after_dedup = len(df)
duplicates_removed = before_dedup - after_dedup

# Save cleaned files
df.to_csv(CLEAN_FILE, index=False)
df.head(1000).to_csv(CLEAN_SAMPLE_FILE, index=False)

print(f"Duplicates removed: {duplicates_removed:,}")
print(f"Cleaned rows saved: {len(df):,}")
print(f"Cleaned columns saved: {len(df.columns):,}")
print(f"Cleaned file saved locally to: {CLEAN_FILE}")
print(f"Cleaned sample file saved to: {CLEAN_SAMPLE_FILE}")

print("\nCleaned dataset preview:")
print(df.head())

print("\nNew derived columns added:")
derived_columns = [
    "declarationYear",
    "declarationMonth",
    "declarationMonthName",
    "declarationQuarter",
    "declarationMonthYear",
    "femaRegion",
]

for col in derived_columns:
    if col in df.columns:
        print(f"- {col}")

print("FEMA data cleaning complete.")