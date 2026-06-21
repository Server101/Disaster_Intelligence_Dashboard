# Cleaned Data Summary

## FEMA Disaster Intelligence Dashboard

This document summarizes the first cleaning step completed for the FEMA Disaster Intelligence Dashboard project. The purpose of this step was to move beyond the raw FEMA data and create a cleaner dataset that can be used for future analysis, Tableau dashboards, Streamlit, and frontend/backend development.

## Cleaning Script Used

The cleaning process was completed using:

`python analytics/scripts/03_clean_data.py`

## Input Data

The script used the raw FEMA disaster declarations dataset saved locally at:

`data/raw/disaster_declarations_raw.csv`

The raw dataset contained:

- 69,931 rows
- 28 columns

## Cleaning Work Completed

The cleaning script completed the following steps:

- Loaded the raw FEMA disaster declarations dataset.
- Converted major date fields into proper date format.
- Standardized text fields such as state, declaration type, incident type, declaration title, and designated area.
- Converted state abbreviations to uppercase.
- Standardized incident type names using title case.
- Standardized designated area values using title case.
- Created new time-based fields from declaration date.
- Created a readable FEMA region label.
- Removed exact duplicate rows if any were found.
- Saved a full cleaned dataset locally.
- Saved a smaller cleaned sample file for GitHub and review.

## New Columns Created

The cleaning process created the following new fields:

- declarationYear
- declarationMonth
- declarationMonthName
- declarationQuarter
- declarationMonthYear
- femaRegion

These fields will make it easier to analyze trends, seasonality, and regional disaster patterns.

## Output Files Created

The script created the following output files:

- `data/cleaned/disaster_declarations_cleaned.csv`
- `data/sample/disaster_declarations_cleaned_sample.csv`

The full cleaned dataset is stored locally and is not intended to be pushed to GitHub. The cleaned sample file is small enough to include in the repository as progress evidence.

## Current Status

At this stage, the project has moved from basic data access and profiling into data preparation. The cleaned dataset is now ready for the next step, which is creating the warehouse-style fact and dimension tables.

## Next Steps

Next, I will begin creating the curated data model for the project. This will include:

- FactDisasterDeclarations
- DimDate
- DimLocation
- DimIncidentType

These tables will support future dashboard development in Tableau, Streamlit, and the React frontend.