import pandas as pd
from pathlib import Path

print("Starting curated table creation...")

BASE_DIR = Path(__file__).resolve().parents[2]

CLEAN_FILE = BASE_DIR / "data" / "cleaned" / "disaster_declarations_cleaned.csv"
CURATED_DIR = BASE_DIR / "data" / "curated"
SAMPLE_DIR = BASE_DIR / "data" / "sample"
DOCS_DIR = BASE_DIR / "docs"

CURATED_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

if not CLEAN_FILE.exists():
    raise FileNotFoundError(
        f"Cleaned data file not found: {CLEAN_FILE}\n"
        "Run analytics/scripts/03_clean_data.py first."
    )

df = pd.read_csv(CLEAN_FILE)

print(f"Cleaned rows loaded: {len(df):,}")
print(f"Cleaned columns loaded: {len(df.columns):,}")

# Convert important date fields again to make sure they are usable
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
        df[col] = pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_convert(None)

# -----------------------------
# DimDate
# -----------------------------
if "declarationDate" not in df.columns:
    raise KeyError("declarationDate column is required to build DimDate.")

date_dim = df[["declarationDate"]].dropna().drop_duplicates().copy()
date_dim["dateKey"] = pd.to_numeric(
    date_dim["declarationDate"].dt.strftime("%Y%m%d"),
    errors="coerce"
).astype("Int64")

date_dim["fullDate"] = date_dim["declarationDate"].dt.date
date_dim["year"] = date_dim["declarationDate"].dt.year
date_dim["month"] = date_dim["declarationDate"].dt.month
date_dim["monthName"] = date_dim["declarationDate"].dt.month_name()
date_dim["quarter"] = date_dim["declarationDate"].dt.quarter
date_dim["monthYear"] = date_dim["declarationDate"].dt.to_period("M").astype(str)

dim_date = date_dim[
    [
        "dateKey",
        "fullDate",
        "year",
        "month",
        "monthName",
        "quarter",
        "monthYear",
    ]
].sort_values("dateKey")

# -----------------------------
# DimLocation
# -----------------------------
location_columns = []

for col in [
    "state",
    "femaRegion",
    "region",
    "designatedArea",
    "fipsStateCode",
    "fipsCountyCode",
    "placeCode",
]:
    if col in df.columns:
        location_columns.append(col)

dim_location = df[location_columns].drop_duplicates().copy()

# Create a readable location key
dim_location = dim_location.reset_index(drop=True)
dim_location["locationKey"] = dim_location.index + 1

# Reorder columns
location_order = ["locationKey"] + location_columns
dim_location = dim_location[location_order]

# -----------------------------
# DimIncidentType
# -----------------------------
if "incidentType" not in df.columns:
    raise KeyError("incidentType column is required to build DimIncidentType.")

incident_columns = ["incidentType"]

if "designatedIncidentTypes" in df.columns:
    incident_columns.append("designatedIncidentTypes")

dim_incident_type = df[incident_columns].drop_duplicates().copy()
dim_incident_type = dim_incident_type.reset_index(drop=True)
dim_incident_type["incidentTypeKey"] = dim_incident_type.index + 1

incident_order = ["incidentTypeKey"] + incident_columns
dim_incident_type = dim_incident_type[incident_order]

# -----------------------------
# FactDisasterDeclarations
# -----------------------------
fact = df.copy()

# Date key
fact["dateKey"] = pd.to_numeric(
    fact["declarationDate"].dt.strftime("%Y%m%d"),
    errors="coerce"
).astype("Int64")

# Add location key by merging on location fields
fact = fact.merge(
    dim_location,
    on=location_columns,
    how="left"
)

# Add incident type key by merging on incident fields
fact = fact.merge(
    dim_incident_type,
    on=incident_columns,
    how="left"
)

# Select fact columns that are useful for analysis
fact_columns = []

for col in [
    "id",
    "femaDeclarationString",
    "disasterNumber",
    "declarationType",
    "declarationTitle",
    "fyDeclared",
    "ihProgramDeclared",
    "iaProgramDeclared",
    "paProgramDeclared",
    "hmProgramDeclared",
    "tribalRequest",
    "declarationRequestNumber",
    "incidentId",
    "dateKey",
    "locationKey",
    "incidentTypeKey",
    "declarationDate",
    "incidentBeginDate",
    "incidentEndDate",
    "disasterCloseoutDate",
    "lastIAFilingDate",
    "lastRefresh",
]:
    if col in fact.columns:
        fact_columns.append(col)

fact_disaster_declarations = fact[fact_columns].copy()

# -----------------------------
# Save full curated tables
# -----------------------------
fact_file = CURATED_DIR / "fact_disaster_declarations.csv"
dim_date_file = CURATED_DIR / "dim_date.csv"
dim_location_file = CURATED_DIR / "dim_location.csv"
dim_incident_file = CURATED_DIR / "dim_incident_type.csv"

fact_disaster_declarations.to_csv(fact_file, index=False)
dim_date.to_csv(dim_date_file, index=False)
dim_location.to_csv(dim_location_file, index=False)
dim_incident_type.to_csv(dim_incident_file, index=False)

# -----------------------------
# Save sample curated tables
# -----------------------------
fact_disaster_declarations.head(1000).to_csv(
    SAMPLE_DIR / "fact_disaster_declarations_sample.csv",
    index=False
)

dim_date.head(1000).to_csv(
    SAMPLE_DIR / "dim_date_sample.csv",
    index=False
)

dim_location.head(1000).to_csv(
    SAMPLE_DIR / "dim_location_sample.csv",
    index=False
)

dim_incident_type.head(1000).to_csv(
    SAMPLE_DIR / "dim_incident_type_sample.csv",
    index=False
)

# -----------------------------
# Create data model summary doc
# -----------------------------
summary_file = DOCS_DIR / "curated_data_model_summary.md"

summary_text = f"""# Curated Data Model Summary

## FEMA Disaster Intelligence Dashboard

This document summarizes the first warehouse-style data model created for the FEMA Disaster Intelligence Dashboard project.

## Purpose

The goal of this step was to organize the cleaned FEMA disaster declaration data into a structure that will be easier to use for Tableau, Streamlit, and future frontend/backend development.

The model follows a simple star-schema style design, with one central fact table and supporting dimension tables.

## Tables Created

### FactDisasterDeclarations

This table contains the main FEMA disaster declaration records. Each row represents a disaster declaration record and connects to the supporting dimension tables through keys.

Rows created: {len(fact_disaster_declarations):,}

### DimDate

This table contains calendar fields based on the FEMA declaration date.

Rows created: {len(dim_date):,}

Fields include:

- dateKey
- fullDate
- year
- month
- monthName
- quarter
- monthYear

### DimLocation

This table contains location-related fields such as state, FEMA region, designated area, and FIPS/location codes.

Rows created: {len(dim_location):,}

### DimIncidentType

This table contains incident type information.

Rows created: {len(dim_incident_type):,}

## Output Files

Full curated files were saved locally in:

`data/curated/`

Sample files were saved in:

`data/sample/`

The sample files can be used as GitHub evidence and for progress report review.

## Current Status

The project now has a cleaned dataset and an initial curated data model. This is an important step because it prepares the data for dashboard development and makes the project easier to scale.

## Next Steps

The next step is to create early analysis outputs from the curated data, including yearly trends, monthly trends, incident type summaries, state summaries, and FEMA region summaries.
"""

summary_file.write_text(summary_text, encoding="utf-8")

print("\nCurated tables created successfully.")
print(f"FactDisasterDeclarations rows: {len(fact_disaster_declarations):,}")
print(f"DimDate rows: {len(dim_date):,}")
print(f"DimLocation rows: {len(dim_location):,}")
print(f"DimIncidentType rows: {len(dim_incident_type):,}")

print("\nFull curated files saved to:")
print(f"- {fact_file}")
print(f"- {dim_date_file}")
print(f"- {dim_location_file}")
print(f"- {dim_incident_file}")

print("\nSample files saved to:")
print(f"- {SAMPLE_DIR / 'fact_disaster_declarations_sample.csv'}")
print(f"- {SAMPLE_DIR / 'dim_date_sample.csv'}")
print(f"- {SAMPLE_DIR / 'dim_location_sample.csv'}")
print(f"- {SAMPLE_DIR / 'dim_incident_type_sample.csv'}")

print(f"\nData model summary saved to: {summary_file}")

print("Curated table creation complete.")