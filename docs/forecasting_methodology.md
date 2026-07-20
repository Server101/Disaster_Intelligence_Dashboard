# FEMA Regional Declaration-Record Forecasting Methodology

## Purpose

The forecasting component estimates future monthly FEMA declaration-record volume for a selected FEMA region. It does not predict whether an individual disaster will occur, where it will occur, how severe it will be, or how much damage it will cause.

## Input data

The forecasting service uses the dashboard-ready FEMA declaration dataset and requires:

- `declarationDate`
- `femaRegion`
- One row for each FEMA declaration record

The service groups the records by calendar month for the selected FEMA region. Missing months between the first and last available month are added with a declaration-record count of zero so the time series remains continuous.

## Forecast method

The project uses a seasonal moving-average method with a limited recent-level adjustment.

For each future month:

1. The service finds the same calendar month in up to five previous years.
2. It calculates the average declaration-record count for those matching months.
3. It compares the most recent 12-month average with the preceding 12-month average.
4. The recent-level ratio is limited to a range of 0.75 through 1.25 so one unusual period does not completely control the forecast.
5. The seasonal average is multiplied by the limited recent-level adjustment.
6. The final estimate is rounded to a whole declaration-record count and cannot fall below zero.

When there are not enough same-month observations, the service uses the most recent 12-month average as the forecast base.

## Estimate range

The lower and upper values are simple uncertainty ranges based on the historical spread for the matching calendar month. When that spread is too small, the service uses a square-root-based minimum uncertainty. The range is included to communicate that the point forecast is not exact.

## Forecast horizon

The user can select a forecast horizon from 6 through 12 months in both the Streamlit application and the React website.

## Outputs

The forecasting service returns:

- FEMA region
- Month
- Historical or forecast record type
- Declaration-record count
- Lower estimate
- Upper estimate
- Forecasting method
- Generation timestamp

The full script output is stored at:

`data/curated/monthly_declaration_forecast.csv`

A smaller review file is stored at:

`data/sample/monthly_declaration_forecast_sample.csv`

## Limitations

- FEMA declaration records are administrative records rather than direct measurements of disaster severity.
- One disaster number may appear in multiple declaration records because separate designated areas are listed.
- Monthly declaration totals can contain extreme spikes.
- A short or incomplete regional history can reduce forecast stability.
- Policy, reporting, climate, population, and emergency-management changes may cause future behavior to differ from historical patterns.
- The uncertainty range is descriptive and is not a formal probability interval.
- Forecast results must not be used as an emergency warning or an individual-disaster prediction.
