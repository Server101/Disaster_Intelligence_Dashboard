import pandas as pd
from pathlib import Path

print("Starting initial FEMA analysis...")

BASE_DIR = Path(__file__).resolve().parents[2]

CURATED_DIR = BASE_DIR / "data" / "curated"
SAMPLE_DIR = BASE_DIR / "data" / "sample"
DOCS_DIR = BASE_DIR / "docs"

SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

FACT_FILE = CURATED_DIR / "fact_disaster_declarations.csv"
DIM_DATE_FILE = CURATED_DIR / "dim_date.csv"
DIM_LOCATION_FILE = CURATED_DIR / "dim_location.csv"
DIM_INCIDENT_FILE = CURATED_DIR / "dim_incident_type.csv"

required_files = [
    FACT_FILE,
    DIM_DATE_FILE,
    DIM_LOCATION_FILE,
    DIM_INCIDENT_FILE,
]

for file in required_files:
    if not file.exists():
        raise FileNotFoundError(
            f"Required curated file not found: {file}\n"
            "Run analytics/scripts/04_create_curated_tables.py first."
        )

fact = pd.read_csv(FACT_FILE)
dim_date = pd.read_csv(DIM_DATE_FILE)
dim_location = pd.read_csv(DIM_LOCATION_FILE)
dim_incident = pd.read_csv(DIM_INCIDENT_FILE)

print(f"Fact rows loaded: {len(fact):,}")
print(f"DimDate rows loaded: {len(dim_date):,}")
print(f"DimLocation rows loaded: {len(dim_location):,}")
print(f"DimIncidentType rows loaded: {len(dim_incident):,}")

# Merge fact table with dimensions for analysis
analysis_df = fact.merge(dim_date, on="dateKey", how="left")
analysis_df = analysis_df.merge(dim_location, on="locationKey", how="left")
analysis_df = analysis_df.merge(dim_incident, on="incidentTypeKey", how="left")

print(f"Analysis dataset rows: {len(analysis_df):,}")
print(f"Analysis dataset columns: {len(analysis_df.columns):,}")

# -----------------------------
# Summary outputs
# -----------------------------

declarations_by_year = (
    analysis_df.groupby("year")
    .size()
    .reset_index(name="declarationCount")
    .sort_values("year")
)

declarations_by_month = (
    analysis_df.groupby(["month", "monthName"])
    .size()
    .reset_index(name="declarationCount")
    .sort_values("month")
)

declarations_by_incident_type = (
    analysis_df.groupby("incidentType")
    .size()
    .reset_index(name="declarationCount")
    .sort_values("declarationCount", ascending=False)
)

declarations_by_state = (
    analysis_df.groupby("state")
    .size()
    .reset_index(name="declarationCount")
    .sort_values("declarationCount", ascending=False)
)

declarations_by_region = (
    analysis_df.groupby("femaRegion")
    .size()
    .reset_index(name="declarationCount")
    .sort_values("declarationCount", ascending=False)
)

top_state_incident_mix = (
    analysis_df.groupby(["state", "incidentType"])
    .size()
    .reset_index(name="declarationCount")
    .sort_values("declarationCount", ascending=False)
    .head(25)
)

# -----------------------------
# Save analysis output files
# -----------------------------

declarations_by_year.to_csv(
    SAMPLE_DIR / "analysis_declarations_by_year.csv",
    index=False
)

declarations_by_month.to_csv(
    SAMPLE_DIR / "analysis_declarations_by_month.csv",
    index=False
)

declarations_by_incident_type.to_csv(
    SAMPLE_DIR / "analysis_declarations_by_incident_type.csv",
    index=False
)

declarations_by_state.to_csv(
    SAMPLE_DIR / "analysis_declarations_by_state.csv",
    index=False
)

declarations_by_region.to_csv(
    SAMPLE_DIR / "analysis_declarations_by_region.csv",
    index=False
)

top_state_incident_mix.to_csv(
    SAMPLE_DIR / "analysis_top_state_incident_mix.csv",
    index=False
)

# -----------------------------
# Create written analysis summary
# -----------------------------

top_year = declarations_by_year.sort_values(
    "declarationCount", ascending=False
).head(1)

top_month = declarations_by_month.sort_values(
    "declarationCount", ascending=False
).head(1)

top_incident = declarations_by_incident_type.head(1)
top_state = declarations_by_state.head(1)
top_region = declarations_by_region.head(1)

summary_file = DOCS_DIR / "initial_analysis_summary.md"

summary_text = f"""# Initial Analysis Summary

## FEMA Disaster Intelligence Dashboard

This document summarizes the first analysis outputs created from the curated FEMA disaster declaration tables.

## Purpose

The goal of this step was to confirm that the cleaned and curated data model can support the main dashboard questions. The analysis focused on yearly trends, monthly patterns, incident types, states, and FEMA regions.

## Source Tables Used

The analysis used the curated warehouse-style tables created in the previous step:

- FactDisasterDeclarations
- DimDate
- DimLocation
- DimIncidentType

These tables were merged using date, location, and incident type keys.

## Analysis Dataset

After joining the fact and dimension tables, the analysis dataset contained:

- Rows: {len(analysis_df):,}
- Columns: {len(analysis_df.columns):,}

## Summary Outputs Created

The script created the following analysis output files:

- `data/sample/analysis_declarations_by_year.csv`
- `data/sample/analysis_declarations_by_month.csv`
- `data/sample/analysis_declarations_by_incident_type.csv`
- `data/sample/analysis_declarations_by_state.csv`
- `data/sample/analysis_declarations_by_region.csv`
- `data/sample/analysis_top_state_incident_mix.csv`

## Early Findings

Based on the first analysis run:

- Highest declaration year: {int(top_year.iloc[0]["year"])} with {int(top_year.iloc[0]["declarationCount"]):,} declarations.
- Highest declaration month: {top_month.iloc[0]["monthName"]} with {int(top_month.iloc[0]["declarationCount"]):,} declarations.
- Most common incident type: {top_incident.iloc[0]["incidentType"]} with {int(top_incident.iloc[0]["declarationCount"]):,} declarations.
- State with the highest number of declarations: {top_state.iloc[0]["state"]} with {int(top_state.iloc[0]["declarationCount"]):,} declarations.
- FEMA region with the highest number of declarations: {top_region.iloc[0]["femaRegion"]} with {int(top_region.iloc[0]["declarationCount"]):,} declarations.

## Current Status

The project now has initial analysis outputs that can support the next stage of dashboard development. These summaries will help guide the Tableau visuals, Streamlit filters, and future frontend dashboard layout.

## Next Steps

Next, I will begin turning these analysis outputs into early visualizations and dashboard planning materials. The next major project steps are:

- Create early charts from the summary outputs.
- Begin planning the Tableau dashboard layout.
- Prepare the first dashboard sections for trends, seasonality, hotspots, and incident type comparisons.
"""

summary_file.write_text(summary_text, encoding="utf-8")

print("\nInitial analysis completed successfully.")

print("\nTop 10 declaration years:")
print(declarations_by_year.sort_values("declarationCount", ascending=False).head(10))

print("\nTop 10 incident types:")
print(declarations_by_incident_type.head(10))

print("\nTop 10 states:")
print(declarations_by_state.head(10))

print("\nDeclarations by FEMA region:")
print(declarations_by_region)

print(f"\nInitial analysis summary saved to: {summary_file}")

print("\nAnalysis output files saved to data/sample/")
print("Initial FEMA analysis complete.")