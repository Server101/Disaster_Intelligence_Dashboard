# Initial Analysis Summary

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

- Rows: 69,931
- Columns: 37

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

- Highest declaration year: 2020 with 9,712 declarations.
- Highest declaration month: September with 11,721 declarations.
- Most common incident type: Severe Storm with 19,311 declarations.
- State with the highest number of declarations: TX with 5,391 declarations.
- FEMA region with the highest number of declarations: Region 4 with 18,465 declarations.

## Current Status

The project now has initial analysis outputs that can support the next stage of dashboard development. These summaries will help guide the Tableau visuals, Streamlit filters, and future frontend dashboard layout.

## Next Steps

Next, I will begin turning these analysis outputs into early visualizations and dashboard planning materials. The next major project steps are:

- Create early charts from the summary outputs.
- Begin planning the Tableau dashboard layout.
- Prepare the first dashboard sections for trends, seasonality, hotspots, and incident type comparisons.
