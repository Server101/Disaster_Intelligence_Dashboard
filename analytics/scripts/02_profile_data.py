import pandas as pd
from pathlib import Path

print("Starting FEMA data profiling...")

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_FILE = BASE_DIR / "data" / "raw" / "disaster_declarations_raw.csv"
DOCS_DIR = BASE_DIR / "docs"
SAMPLE_DIR = BASE_DIR / "data" / "sample"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

PROFILE_REPORT = DOCS_DIR / "data_profile_summary.md"
TOP_INCIDENTS_FILE = SAMPLE_DIR / "top_incident_types.csv"
TOP_STATES_FILE = SAMPLE_DIR / "top_states.csv"
TOP_YEARS_FILE = SAMPLE_DIR / "declarations_by_year.csv"

if not RAW_FILE.exists():
    raise FileNotFoundError(
        f"Raw data file not found: {RAW_FILE}\n"
        "Run analytics/scripts/01_fetch_fema_data.py first."
    )

df = pd.read_csv(RAW_FILE)

print(f"Rows: {len(df):,}")
print(f"Columns: {len(df.columns):,}")

# Convert important date fields
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

# Create useful time fields
if "declarationDate" in df.columns:
    df["declarationYear"] = df["declarationDate"].dt.year
    df["declarationMonth"] = df["declarationDate"].dt.month
    df["declarationQuarter"] = df["declarationDate"].dt.quarter
    df["declarationMonthYear"] = df["declarationDate"].dt.to_period("M").astype(str)

# Basic profile values
total_rows = len(df)
total_columns = len(df.columns)
duplicate_rows = df.duplicated().sum()

date_min = df["declarationDate"].min() if "declarationDate" in df.columns else None
date_max = df["declarationDate"].max() if "declarationDate" in df.columns else None

top_incident_types = df["incidentType"].value_counts().head(10) if "incidentType" in df.columns else None
top_states = df["state"].value_counts().head(10) if "state" in df.columns else None
declarations_by_year = df["declarationYear"].value_counts().sort_index() if "declarationYear" in df.columns else None
missing_values = df.isna().sum().sort_values(ascending=False).head(15)

# Save small CSV summaries
if top_incident_types is not None:
    top_incident_types.reset_index().to_csv(
        TOP_INCIDENTS_FILE,
        index=False,
        header=["incidentType", "count"]
    )

if top_states is not None:
    top_states.reset_index().to_csv(
        TOP_STATES_FILE,
        index=False,
        header=["state", "count"]
    )

if declarations_by_year is not None:
    declarations_by_year.reset_index().to_csv(
        TOP_YEARS_FILE,
        index=False,
        header=["declarationYear", "count"]
    )

# Build markdown report
report_lines = []

report_lines.append("# FEMA Disaster Declarations Data Profile Summary\n")
report_lines.append("This report summarizes the initial data profiling completed for the FEMA Disaster Intelligence Dashboard project.\n")

report_lines.append("## Dataset Size\n")
report_lines.append(f"- Total rows: {total_rows:,}")
report_lines.append(f"- Total columns: {total_columns:,}")
report_lines.append(f"- Duplicate rows detected: {duplicate_rows:,}\n")

report_lines.append("## Declaration Date Range\n")
report_lines.append(f"- Earliest declaration date: {date_min}")
report_lines.append(f"- Latest declaration date: {date_max}\n")

report_lines.append("## Columns Reviewed\n")
for col in df.columns:
    report_lines.append(f"- {col}")
report_lines.append("")

report_lines.append("## Top 10 Incident Types\n")
if top_incident_types is not None:
    for incident, count in top_incident_types.items():
        report_lines.append(f"- {incident}: {count:,}")
else:
    report_lines.append("- incidentType column not found.")
report_lines.append("")

report_lines.append("## Top 10 States by Declaration Count\n")
if top_states is not None:
    for state, count in top_states.items():
        report_lines.append(f"- {state}: {count:,}")
else:
    report_lines.append("- state column not found.")
report_lines.append("")

report_lines.append("## Top Missing Value Counts\n")
for col, count in missing_values.items():
    report_lines.append(f"- {col}: {count:,}")
report_lines.append("")

report_lines.append("## Initial Notes\n")
report_lines.append("- The dataset was successfully loaded from the local raw FEMA CSV file.")
report_lines.append("- The main fields needed for the project are available, including declaration date, incident type, state, region, and designated area.")
report_lines.append("- Date fields were converted into datetime format for future trend and seasonality analysis.")
report_lines.append("- Additional time fields were created, including declaration year, month, quarter, and month-year.")
report_lines.append("- This profile will support the next step of cleaning the data and preparing curated tables for dashboards.\n")

PROFILE_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

print("\nTop 10 incident types:")
print(top_incident_types)

print("\nTop 10 states:")
print(top_states)

print("\nTop missing value counts:")
print(missing_values)

print(f"\nProfile report saved to: {PROFILE_REPORT}")
print(f"Top incident types saved to: {TOP_INCIDENTS_FILE}")
print(f"Top states saved to: {TOP_STATES_FILE}")
print(f"Declarations by year saved to: {TOP_YEARS_FILE}")

print("FEMA data profiling complete.")