from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

FEMA_DATA_URL = os.getenv(
    "FEMA_DATA_URL",
    "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries.csv",
)

DATE_COLUMNS = [
    "declarationDate",
    "incidentBeginDate",
    "incidentEndDate",
    "disasterCloseoutDate",
    "lastIAFilingDate",
    "lastRefresh",
]

TEXT_COLUMNS = [
    "femaDeclarationString",
    "state",
    "declarationType",
    "incidentType",
    "declarationTitle",
    "designatedArea",
    "designatedIncidentTypes",
]

DASHBOARD_COLUMNS = [
    "id",
    "femaDeclarationString",
    "disasterNumber",
    "state",
    "declarationType",
    "declarationTypeLabel",
    "declarationDate",
    "declarationYear",
    "declarationMonth",
    "declarationMonthName",
    "declarationQuarter",
    "declarationMonthYear",
    "fyDeclared",
    "incidentType",
    "declarationTitle",
    "designatedArea",
    "region",
    "femaRegion",
    "incidentBeginDate",
    "incidentEndDate",
    "disasterCloseoutDate",
    "ihProgramDeclared",
    "iaProgramDeclared",
    "paProgramDeclared",
    "hmProgramDeclared",
    "tribalRequest",
    "fipsStateCode",
    "fipsCountyCode",
    "placeCode",
    "declarationRequestNumber",
    "lastIAFilingDate",
    "incidentId",
    "designatedIncidentTypes",
    "lastRefresh",
]

DECLARATION_TYPE_LABELS = {
    "DR": "Major Disaster",
    "EM": "Emergency",
    "FM": "Fire Management Assistance",
}


@dataclass(frozen=True)
class DataLoadResult:
    frame: pd.DataFrame
    source_label: str
    is_sample: bool


def _clean_text(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "None": pd.NA,
            "<NA>": pd.NA,
        }
    )


def _read_local_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def _read_remote_csv(url: str) -> pd.DataFrame:
    response = requests.get(
        url,
        headers={
            "User-Agent": "FEMA-Disaster-Intelligence-Dashboard/1.0",
            "Accept-Encoding": "gzip, deflate",
        },
        timeout=(15, 180),
    )
    response.raise_for_status()
    return pd.read_csv(BytesIO(response.content), low_memory=False)


def normalize_fema_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Prepare FEMA records for filtering, metrics, charts, and downloads."""
    df = frame.copy()

    required_columns = [
        "disasterNumber",
        "state",
        "declarationType",
        "declarationDate",
        "incidentType",
        "designatedArea",
        "region",
    ]

    for column in required_columns:
        if column not in df.columns:
            df[column] = pd.NA

    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
                utc=True,
            ).dt.tz_convert(None)

    for column in TEXT_COLUMNS:
        if column in df.columns:
            df[column] = _clean_text(df[column])

    df["state"] = _clean_text(df["state"]).str.upper()
    df["declarationType"] = _clean_text(df["declarationType"]).str.upper()
    df["incidentType"] = _clean_text(df["incidentType"]).str.title()
    df["designatedArea"] = _clean_text(df["designatedArea"]).str.title()

    df["declarationTypeLabel"] = (
        df["declarationType"]
        .map(DECLARATION_TYPE_LABELS)
        .fillna(df["declarationType"])
        .fillna("Not Reported")
    )

    df["region"] = pd.to_numeric(df["region"], errors="coerce").astype("Int64")
    df["femaRegion"] = df["region"].map(
        lambda value: f"Region {int(value)}" if pd.notna(value) else "Not Reported"
    )

    declaration_date = df["declarationDate"]
    df["declarationYear"] = declaration_date.dt.year.astype("Int64")
    df["declarationMonth"] = declaration_date.dt.month.astype("Int64")
    df["declarationMonthName"] = declaration_date.dt.month_name()
    df["declarationQuarter"] = declaration_date.dt.quarter.astype("Int64")
    df["declarationMonthYear"] = declaration_date.dt.to_period("M").astype("string")

    for column in [
        "state",
        "incidentType",
        "declarationTitle",
        "designatedArea",
    ]:
        if column in df.columns:
            df[column] = df[column].fillna("Not Reported")

    if "id" in df.columns and df["id"].notna().any():
        df = df.drop_duplicates(subset=["id"], keep="last")
    else:
        df = df.drop_duplicates()

    available_columns = [column for column in DASHBOARD_COLUMNS if column in df.columns]
    df = df[available_columns].copy()

    if "declarationDate" in df.columns:
        df = df.sort_values("declarationDate", ascending=False, na_position="last")

    return df.reset_index(drop=True)


def load_fema_data(base_dir: Path, allow_remote: bool = True) -> DataLoadResult:
    """Load the best available full dataset and fall back to a repository sample."""
    base_dir = Path(base_dir)

    full_candidates = [
        (
            base_dir / "data" / "curated" / "fema_dashboard_dataset.csv",
            "Local dashboard dataset",
        ),
        (
            base_dir / "data" / "cleaned" / "disaster_declarations_cleaned.csv",
            "Local cleaned dataset",
        ),
        (
            base_dir / "data" / "raw" / "disaster_declarations_raw.csv",
            "Local raw FEMA dataset",
        ),
    ]

    for path, label in full_candidates:
        if path.exists():
            frame = normalize_fema_data(_read_local_csv(path))
            if not frame.empty:
                return DataLoadResult(frame=frame, source_label=label, is_sample=False)

    remote_error: Exception | None = None
    if allow_remote:
        try:
            frame = normalize_fema_data(_read_remote_csv(FEMA_DATA_URL))
            if not frame.empty:
                return DataLoadResult(
                    frame=frame,
                    source_label="FEMA OpenFEMA live CSV",
                    is_sample=False,
                )
        except Exception as exc:
            remote_error = exc

    sample_candidates = [
        (
            base_dir / "data" / "sample" / "fema_dashboard_dataset_sample.csv",
            "Repository dashboard sample",
        ),
        (
            base_dir / "data" / "sample" / "disaster_declarations_cleaned_sample.csv",
            "Repository cleaned sample",
        ),
        (
            base_dir / "data" / "sample" / "disaster_declarations_sample.csv",
            "Repository raw sample",
        ),
    ]

    for path, label in sample_candidates:
        if path.exists():
            frame = normalize_fema_data(_read_local_csv(path))
            if not frame.empty:
                return DataLoadResult(frame=frame, source_label=label, is_sample=True)

    message = "No FEMA dataset could be loaded."
    if remote_error is not None:
        message += f" Remote download error: {remote_error}"
    raise RuntimeError(message)


def apply_filters(
    frame: pd.DataFrame,
    start_date,
    end_date,
    states: Iterable[str],
    regions: Iterable[str],
    incident_types: Iterable[str],
    declaration_types: Iterable[str],
) -> pd.DataFrame:
    """Apply the dashboard filters and return a separate filtered frame."""
    filtered = frame.copy()

    start_timestamp = pd.Timestamp(start_date)
    end_timestamp = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)

    filtered = filtered[
        filtered["declarationDate"].between(start_timestamp, end_timestamp, inclusive="both")
    ]

    selected_states = list(states)
    selected_regions = list(regions)
    selected_incidents = list(incident_types)
    selected_declaration_types = list(declaration_types)

    if selected_states:
        filtered = filtered[filtered["state"].isin(selected_states)]
    if selected_regions:
        filtered = filtered[filtered["femaRegion"].isin(selected_regions)]
    if selected_incidents:
        filtered = filtered[filtered["incidentType"].isin(selected_incidents)]
    if selected_declaration_types:
        filtered = filtered[
            filtered["declarationTypeLabel"].isin(selected_declaration_types)
        ]

    return filtered.reset_index(drop=True)


def sort_region_labels(values: Iterable[str]) -> list[str]:
    """Sort FEMA region labels in numeric order and place missing values last."""
    def region_key(label: str) -> tuple[int, str]:
        if label.startswith("Region "):
            try:
                return int(label.split(" ", 1)[1]), label
            except ValueError:
                pass
        return 999, label

    return sorted(set(values), key=region_key)
