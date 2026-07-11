# Dashboard Data Dictionary

## Purpose

This dictionary documents the fields prepared for the FEMA Disaster Intelligence Streamlit application and future Tableau dashboard.

| Field | Type | Description | Dashboard Use |
|---|---|---|---|
| `id` | Text | Unique OpenFEMA record identifier when available | Duplicate control |
| `femaDeclarationString` | Text | FEMA declaration identifier containing declaration type, number, and state | Record reference |
| `disasterNumber` | Integer | FEMA disaster number | Unique disaster metric |
| `state` | Text | State or territory abbreviation | Filter and geographic comparison |
| `declarationType` | Text | FEMA declaration type code such as DR, EM, or FM | Filter |
| `declarationTypeLabel` | Text | Readable declaration type label | Chart and filter |
| `declarationDate` | Date | Official declaration date | Date filter and trends |
| `declarationYear` | Integer | Year derived from the declaration date | Annual trend and KPI |
| `declarationMonth` | Integer | Month number derived from the declaration date | Seasonality analysis |
| `declarationMonthName` | Text | Month name derived from the declaration date | Seasonality chart |
| `declarationQuarter` | Integer | Calendar quarter derived from the declaration date | Future quarterly analysis |
| `declarationMonthYear` | Text | Month and year in YYYY-MM format | Monthly trend |
| `fyDeclared` | Integer | Federal fiscal year of the declaration | Supporting analysis |
| `incidentType` | Text | Primary FEMA incident category | KPI, filter, and comparison chart |
| `declarationTitle` | Text | FEMA declaration title | Record details |
| `designatedArea` | Text | County, parish, tribal area, municipality, or other designated location | Record details |
| `region` | Integer | Numeric FEMA region | Data validation |
| `femaRegion` | Text | Readable FEMA region label | Filter and regional chart |
| `incidentBeginDate` | Date | Reported incident start date | Supporting analysis |
| `incidentEndDate` | Date | Reported incident end date | Supporting analysis |
| `disasterCloseoutDate` | Date | FEMA disaster closeout date when available | Supporting analysis |
| `ihProgramDeclared` | Integer | Individuals and Households Program indicator | Future program analysis |
| `iaProgramDeclared` | Integer | Individual Assistance Program indicator | Future program analysis |
| `paProgramDeclared` | Integer | Public Assistance Program indicator | Future program analysis |
| `hmProgramDeclared` | Integer | Hazard Mitigation Program indicator | Future program analysis |
| `tribalRequest` | Integer | Tribal request indicator | Future program analysis |
| `fipsStateCode` | Integer | State FIPS code | Geographic reference |
| `fipsCountyCode` | Integer | County FIPS code | Geographic reference |
| `placeCode` | Integer | FEMA place code | Geographic reference |
| `declarationRequestNumber` | Integer | FEMA declaration request number | Record reference |
| `lastIAFilingDate` | Date | Final filing date for Individual Assistance when available | Supporting analysis |
| `incidentId` | Text | FEMA incident identifier | Record reference |
| `designatedIncidentTypes` | Text | Additional designated incident categories | Supporting analysis |
| `lastRefresh` | Date | OpenFEMA record refresh timestamp | Data freshness note |

## Counting Note

A declaration record is one row in the OpenFEMA dataset. A unique disaster is counted using `disasterNumber`. One disaster number may appear in several declaration records because multiple designated areas can be listed separately.
