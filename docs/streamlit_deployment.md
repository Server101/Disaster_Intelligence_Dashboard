# Streamlit Launch and Hosting Guide

## Run the application locally

Open a terminal in the repository root and run:

```bash
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Activate the environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the project packages:

```bash
python -m pip install -r requirements.txt
```

Create the dashboard-ready dataset from the best available FEMA file:

```bash
python analytics/scripts/06_create_dashboard_dataset.py
```

Start Streamlit:

```bash
python -m streamlit run analytics/streamlit/app.py
```

Open the local address displayed in the terminal, normally:

```text
http://localhost:8501
```

## Host the application publicly

Use Streamlit Community Cloud for the public Progress Report 1 link.

1. Push the changed files to the GitHub repository.
2. Confirm that `requirements.txt` is in the repository root.
3. Confirm that `analytics/streamlit/app.py` is committed.
4. Sign in to Streamlit Community Cloud with the GitHub account connected to the repository.
5. Select **Create app**.
6. Select the repository and branch.
7. Enter this app file path:

```text
analytics/streamlit/app.py
```

8. Choose an available application URL.
9. Deploy the app.
10. Wait for the dependency installation and startup process to finish.
11. Open the public URL in an incognito browser window.
12. Test filters, KPI cards, charts, the table, and the CSV download.

## Data loading behavior

The hosted app attempts these sources in order:

1. `data/curated/fema_dashboard_dataset.csv`
2. `data/cleaned/disaster_declarations_cleaned.csv`
3. `data/raw/disaster_declarations_raw.csv`
4. The official FEMA OpenFEMA CSV
5. Repository sample files

The existing `.gitignore` keeps the large local raw, cleaned, and curated CSV files out of GitHub. The hosted app can still use the full FEMA dataset because it downloads the official CSV when local full files are unavailable.

## Deployment troubleshooting

### Module import error

Confirm that the `backend` folder, `backend/__init__.py`, and `backend/fema_data_service.py` are committed.

### Missing package error

Add the imported package to `requirements.txt`, push the change, and reboot the Streamlit app.

### File not found error

Confirm the app path is exactly:

```text
analytics/streamlit/app.py
```

### Live FEMA download unavailable

The app automatically opens with the repository sample and displays a warning. Reboot the app later to retry the live source.

### App remains private

Open the Streamlit sharing settings and allow public access before submitting the link.
