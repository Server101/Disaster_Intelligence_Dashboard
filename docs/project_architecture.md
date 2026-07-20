# FEMA Disaster Intelligence Project Architecture

## System flow

```text
OpenFEMA Disaster Declarations Summaries v2
                    |
                    v
Python extraction, profiling, cleaning, and curation
                    |
                    v
Amazon S3 project bucket
  raw/ cleaned/ curated/ dashboard/ forecasts/ website/ logs/
                    |
          +---------+---------+
          |                   |
          v                   v
Regional forecast service   FastAPI on Amazon EC2
          |                   |
          +---------+---------+
                    |
                    v
       React website, Streamlit, and Tableau
                    |
                    v
 Amazon CloudFront public HTTPS address
```

## Data pipeline

1. `01_fetch_fema_data.py` retrieves the OpenFEMA declaration dataset.
2. `02_profile_data.py` profiles fields, missing values, years, states, and incident categories.
3. `03_clean_data.py` standardizes dates, labels, locations, and derived time fields.
4. `04_create_curated_tables.py` creates the fact and dimension tables.
5. `05_initial_analysis.py` creates reviewable summary outputs.
6. `06_create_dashboard_dataset.py` creates the flattened dashboard-ready dataset.
7. `07_forecast_declarations.py` creates regional monthly forecast output.

## Storage layer

One private S3 bucket stores the project artifacts by prefix:

- `raw/`
- `cleaned/`
- `curated/`
- `dashboard/`
- `forecasts/`
- `website/`
- `logs/`

The FastAPI service reads only the dashboard and forecast prefixes through an EC2 IAM role. The website prefix is read by CloudFront through Origin Access Control.

## API layer

FastAPI runs on an EC2 instance behind Nginx. Nginx listens on port 80 and forwards `/api/*` requests to Uvicorn on `127.0.0.1:8000`.

The API provides health, metadata, summary, trend, region, state, incident-type, seasonality, and forecast responses in JSON.

## React website

The React site includes:

- Project overview and research question
- Live or snapshot data-source status
- Year and FEMA-region filters
- KPI cards
- Annual declaration-record trend
- Incident-type ranking
- FEMA-region comparison
- State and territory hotspots
- Monthly seasonality
- Regional forecast controls
- Historical and forecast line chart
- Forecast output table
- Forecast CSV download
- Streamlit popout viewer
- Tableau popout viewer
- AWS architecture and data limitations

A bundled analytics snapshot allows the website to display meaningful project results before the API is available. When the API responds successfully, the website replaces the snapshot with live API results.

## Streamlit application

Streamlit provides the detailed exploratory dashboard with multiselect filters, KPI cards, charts, the filtered record table, regional forecasting, and CSV downloads. It can retrieve forecast output from the AWS API when `FEMA_API_BASE_URL` is configured.

## Tableau dashboard

The Tableau dashboard is designed for presentation-oriented analysis and includes KPI cards, a state map, annual trends, incident-type comparisons, FEMA-region comparisons, seasonality, hotspot rankings, and filters.

The React website reads the published Tableau URL from `VITE_TABLEAU_URL` and displays it in an in-page iframe popout. If Tableau blocks the iframe, the same popout provides an external-open fallback.

## CloudFront distribution

The project uses the default CloudFront domain and does not require a custom domain.

- Default behavior: private S3 website origin
- `/api/*` behavior: EC2 custom origin
- Viewer protocol: redirect HTTP to HTTPS
- S3 access: Origin Access Control
- API caching: disabled
- Website caching: enabled
- Default root object: `index.html`

## Security

- S3 Block Public Access remains enabled.
- CloudFront is the only public reader of the website objects.
- EC2 uses an IAM role and temporary credentials instead of saved access keys.
- The EC2 role is limited to `dashboard/*` and `forecasts/*` read access.
- Port 8000 is not exposed publicly.
- Port 80 can be restricted to the CloudFront origin-facing managed prefix list.
- SSH access is restricted to the administrator's current IP, or EC2 Systems Manager can be used instead.
- No account numbers, access keys, secrets, or credentials belong in GitHub.
