# FEMA Disaster Intelligence API Documentation

## Overview

The backend is a FastAPI service that reads the dashboard-ready dataset and forecast output from Amazon S3 when AWS configuration is available. During local development, it falls back to the best available local dataset, the OpenFEMA CSV source, or the repository sample.

The service supports direct routes such as `/health` and CloudFront-compatible routes such as `/api/health`.

## Local startup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Interactive API documentation:

`http://127.0.0.1:8000/api/docs`

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `AWS_REGION` | AWS Region used by the S3 client | `us-east-1` |
| `FEMA_S3_BUCKET` | Project S3 bucket name | Empty; local/remote fallback is used |
| `FEMA_S3_DASHBOARD_KEY` | Dashboard dataset object key | `dashboard/fema_dashboard_dataset.csv` |
| `FEMA_S3_FORECAST_KEY` | Forecast object key | `forecasts/monthly_declaration_forecast.csv` |
| `FEMA_DATA_CACHE_SECONDS` | In-memory dataset and forecast cache lifetime | `21600` |
| `FEMA_ALLOWED_ORIGINS` | Comma-separated browser origins permitted by CORS | Local React, local Streamlit, and public Streamlit |
| `FEMA_DATA_URL` | OpenFEMA CSV fallback source | FEMA Disaster Declarations Summaries v2 CSV |

Do not store AWS access keys in the project `.env` file. The EC2 deployment uses an IAM role attached to the instance.

## Endpoints

### `GET /api/health`

Returns service status, active data source, sample-mode status, record count, and check time.

### `GET /api/metadata`

Returns the available date range, years, states, FEMA regions, incident types, declaration types, data source, and sample-mode status.

### `GET /api/summary`

Returns:

- Declaration-record count
- Unique disaster-number count
- Top state or territory
- Top incident type
- Peak declaration year

Optional query parameters:

- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `state=FL`
- `region=Region 4`
- `incident_type=Hurricane`
- `declaration_type=Major Disaster`

Example:

`/api/summary?start_date=2015-01-01&end_date=2026-12-31&region=Region%204`

### `GET /api/trends`

Returns declaration-record totals by year or month.

Query parameters:

- `grain=year` or `grain=month`
- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `region=Region 4`

### `GET /api/regions`

Returns declaration-record totals for FEMA regions. Optional `start_date` and `end_date` parameters limit the comparison period.

### `GET /api/states`

Returns a ranked list of states and territories.

Query parameters:

- `limit=1` through `50`
- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `region=Region 4`

### `GET /api/incident-types`

Returns a ranked list of incident types.

Query parameters:

- `limit=1` through `50`
- `start_date=YYYY-MM-DD`
- `end_date=YYYY-MM-DD`
- `region=Region 4`

### `GET /api/seasonality`

Returns January through December declaration-record totals. Optional date and region parameters can be applied.

### `GET /api/forecast`

Returns historical monthly values and a 6–12 month regional forecast.

Required or supported query parameters:

- `region=Region 4`
- `horizon=6` through `12`

Example:

`/api/forecast?region=Region%204&horizon=12`

## CloudFront routing

The React website uses `/api` as its production API base path. CloudFront routes `/api/*` requests to the EC2 origin and sends all other website requests to the private S3 origin.

The frontend production variable is:

```text
VITE_API_BASE_URL=/api
```

## Error behavior

- `400`: Invalid date order or invalid query value
- `404`: No matching records or an unavailable forecast region
- `500`: Forecast calculation failure
- `503`: Dataset could not be loaded
