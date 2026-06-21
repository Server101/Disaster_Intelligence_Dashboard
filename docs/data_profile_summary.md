# FEMA Disaster Declarations Data Profile Summary

This report summarizes the initial data profiling completed for the FEMA Disaster Intelligence Dashboard project.

## Dataset Size

- Total rows: 69,931
- Total columns: 32
- Duplicate rows detected: 0

## Declaration Date Range

- Earliest declaration date: 1953-05-02 00:00:00+00:00
- Latest declaration date: 2026-05-29 00:00:00+00:00

## Columns Reviewed

- femaDeclarationString
- disasterNumber
- state
- declarationType
- declarationDate
- fyDeclared
- incidentType
- declarationTitle
- ihProgramDeclared
- iaProgramDeclared
- paProgramDeclared
- hmProgramDeclared
- incidentBeginDate
- incidentEndDate
- disasterCloseoutDate
- tribalRequest
- fipsStateCode
- fipsCountyCode
- placeCode
- designatedArea
- declarationRequestNumber
- lastIAFilingDate
- incidentId
- region
- designatedIncidentTypes
- lastRefresh
- hash
- id
- declarationYear
- declarationMonth
- declarationQuarter
- declarationMonthYear

## Top 10 Incident Types

- Severe Storm: 19,311
- Hurricane: 13,726
- Flood: 11,288
- Biological: 7,857
- Fire: 3,876
- Snowstorm: 3,707
- Severe Ice Storm: 2,956
- Tornado: 1,623
- Winter Storm: 1,374
- Drought: 1,292

## Top 10 States by Declaration Count

- TX: 5,391
- KY: 3,373
- MO: 2,830
- FL: 2,794
- GA: 2,768
- VA: 2,756
- LA: 2,671
- OK: 2,593
- NC: 2,431
- MS: 2,129

## Top Missing Value Counts

- lastIAFilingDate: 50,260
- designatedIncidentTypes: 47,812
- disasterCloseoutDate: 16,893
- incidentEndDate: 514
- declarationDate: 0
- fyDeclared: 0
- femaDeclarationString: 0
- disasterNumber: 0
- declarationTitle: 0
- incidentType: 0
- ihProgramDeclared: 0
- iaProgramDeclared: 0
- hmProgramDeclared: 0
- paProgramDeclared: 0
- state: 0

## Initial Notes

- The dataset was successfully loaded from the local raw FEMA CSV file.
- The main fields needed for the project are available, including declaration date, incident type, state, region, and designated area.
- Date fields were converted into datetime format for future trend and seasonality analysis.
- Additional time fields were created, including declaration year, month, quarter, and month-year.
- This profile will support the next step of cleaning the data and preparing curated tables for dashboards.
