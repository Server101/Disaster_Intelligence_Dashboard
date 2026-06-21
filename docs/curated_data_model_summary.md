# Curated Data Model Summary

## FEMA Disaster Intelligence Dashboard

This document summarizes the first warehouse-style data model created for the FEMA Disaster Intelligence Dashboard project.

## Purpose

The goal of this step was to organize the cleaned FEMA disaster declaration data into a structure that will be easier to use for Tableau, Streamlit, and future frontend/backend development.

The model follows a simple star-schema style design, with one central fact table and supporting dimension tables.

## Tables Created

### FactDisasterDeclarations

This table contains the main FEMA disaster declaration records. Each row represents a disaster declaration record and connects to the supporting dimension tables through keys.

Rows created: 69,931

### DimDate

This table contains calendar fields based on the FEMA declaration date.

Rows created: 3,595

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

Rows created: 4,304

### DimIncidentType

This table contains incident type information.

Rows created: 212

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
