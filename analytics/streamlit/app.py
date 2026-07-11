from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.fema_data_service import apply_filters, load_fema_data, sort_region_labels

st.set_page_config(
    page_title="Disaster Intelligence",
    page_icon="🌪️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1500px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }
        .hero-panel {
            padding: 1.8rem 2rem;
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(30, 64, 175, 0.10), rgba(14, 116, 144, 0.08));
            margin-bottom: 1.2rem;
        }
        .hero-panel h1 {
            margin: 0 0 0.4rem 0;
            font-size: 2.35rem;
        }
        .hero-panel p {
            margin: 0;
            font-size: 1.05rem;
            line-height: 1.65;
        }
        [data-testid="stMetric"] {
            border: 1px solid rgba(49, 51, 63, 0.14);
            border-radius: 14px;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.03);
        }
        .status-note {
            padding: 0.8rem 1rem;
            border-radius: 12px;
            background: rgba(14, 116, 144, 0.08);
            border: 1px solid rgba(14, 116, 144, 0.20);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=21600, show_spinner="Loading FEMA declaration data...")
def load_app_data() -> tuple[pd.DataFrame, str, bool]:
    result = load_fema_data(ROOT_DIR, allow_remote=True)
    return result.frame, result.source_label, result.is_sample


try:
    data, source_label, is_sample = load_app_data()
except Exception as exc:
    st.error("The FEMA dataset could not be loaded.")
    st.exception(exc)
    st.stop()

valid_dates = data["declarationDate"].dropna()
if valid_dates.empty:
    st.error("The dataset does not contain usable declaration dates.")
    st.stop()

minimum_date = valid_dates.min().date()
maximum_date = valid_dates.max().date()

st.markdown(
    """
    <div class="hero-panel">
        <h1>FEMA Disaster Intelligence Dashboard</h1>
        <p>
            Explore FEMA disaster declaration records across time, geography, incident type,
            declaration type, and FEMA region. Filters update every metric, chart, and table.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.header("Dashboard Filters")
selected_dates = st.sidebar.date_input(
    "Declaration date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    selected_start_date, selected_end_date = selected_dates
else:
    selected_start_date = selected_dates
    selected_end_date = selected_dates

state_options = sorted(data["state"].dropna().unique().tolist())
region_options = sort_region_labels(data["femaRegion"].dropna().unique().tolist())
incident_options = sorted(data["incidentType"].dropna().unique().tolist())
declaration_type_options = sorted(
    data["declarationTypeLabel"].dropna().unique().tolist()
)

selected_states = st.sidebar.multiselect("State or territory", state_options)
selected_regions = st.sidebar.multiselect("FEMA region", region_options)
selected_incidents = st.sidebar.multiselect("Incident type", incident_options)
selected_declaration_types = st.sidebar.multiselect(
    "Declaration type",
    declaration_type_options,
)

top_count = st.sidebar.slider("Number of categories to display", 5, 20, 10)

filtered = apply_filters(
    data,
    selected_start_date,
    selected_end_date,
    selected_states,
    selected_regions,
    selected_incidents,
    selected_declaration_types,
)

st.sidebar.divider()
st.sidebar.caption(f"Data source: {source_label}")
if is_sample:
    st.sidebar.warning(
        "The live FEMA download was unavailable, so the repository sample is displayed."
    )
else:
    st.sidebar.success("Full FEMA data is loaded.")

if "lastRefresh" in data.columns and data["lastRefresh"].notna().any():
    latest_refresh = data["lastRefresh"].max().strftime("%B %d, %Y")
    st.sidebar.caption(f"Latest source refresh: {latest_refresh}")

if filtered.empty:
    st.warning("No declaration records match the selected filters.")
    st.stop()

record_count = len(filtered)
unique_disasters = filtered["disasterNumber"].nunique(dropna=True)
top_state = filtered["state"].value_counts().idxmax()
top_incident = filtered["incidentType"].value_counts().idxmax()
peak_year = int(filtered["declarationYear"].value_counts().idxmax())

metric_columns = st.columns(5)
metric_columns[0].metric("Declaration Records", f"{record_count:,}")
metric_columns[1].metric("Unique Disaster Numbers", f"{unique_disasters:,}")
metric_columns[2].metric("Top State or Territory", top_state)
metric_columns[3].metric("Top Incident Type", top_incident)
metric_columns[4].metric("Peak Declaration Year", peak_year)

st.markdown(
    """
    <div class="status-note">
        Declaration records and unique disasters are separate measures. A single FEMA disaster
        number can appear in multiple rows because declarations may list several designated areas.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")
overview_tab, trends_tab, geography_tab, data_tab = st.tabs(
    ["Overview", "Trends and Seasonality", "Geography and Regions", "Filtered Data"]
)

with overview_tab:
    left_chart, right_chart = st.columns(2)

    yearly = (
        filtered.dropna(subset=["declarationYear"])
        .groupby("declarationYear")
        .size()
        .reset_index(name="Declaration Records")
        .sort_values("declarationYear")
    )
    yearly["declarationYear"] = yearly["declarationYear"].astype(int)

    yearly_figure = px.line(
        yearly,
        x="declarationYear",
        y="Declaration Records",
        markers=True,
        labels={"declarationYear": "Declaration Year"},
        title="Declaration Records by Year",
    )
    yearly_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    left_chart.plotly_chart(yearly_figure, width="stretch")

    incidents = (
        filtered["incidentType"]
        .value_counts()
        .head(top_count)
        .sort_values()
        .rename_axis("Incident Type")
        .reset_index(name="Declaration Records")
    )
    incident_figure = px.bar(
        incidents,
        x="Declaration Records",
        y="Incident Type",
        orientation="h",
        title=f"Top {top_count} Incident Types",
        text_auto=",",
    )
    incident_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    right_chart.plotly_chart(incident_figure, width="stretch")

    declaration_types = (
        filtered["declarationTypeLabel"]
        .value_counts()
        .rename_axis("Declaration Type")
        .reset_index(name="Declaration Records")
    )
    declaration_figure = px.bar(
        declaration_types,
        x="Declaration Type",
        y="Declaration Records",
        title="Declaration Records by Declaration Type",
        text_auto=",",
    )
    declaration_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(declaration_figure, width="stretch")

with trends_tab:
    monthly_trend = (
        filtered.dropna(subset=["declarationMonthYear"])
        .groupby("declarationMonthYear")
        .size()
        .reset_index(name="Declaration Records")
    )
    monthly_trend["Month"] = pd.to_datetime(
        monthly_trend["declarationMonthYear"],
        errors="coerce",
    )
    monthly_trend = monthly_trend.dropna(subset=["Month"]).sort_values("Month")

    monthly_figure = px.area(
        monthly_trend,
        x="Month",
        y="Declaration Records",
        title="Monthly Declaration Record Trend",
    )
    monthly_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(monthly_figure, width="stretch")

    month_order = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    seasonality = (
        filtered.groupby("declarationMonthName")
        .size()
        .reindex(month_order, fill_value=0)
        .rename_axis("Month")
        .reset_index(name="Declaration Records")
    )
    seasonality_figure = px.bar(
        seasonality,
        x="Month",
        y="Declaration Records",
        title="Declaration Records by Month of Year",
        text_auto=",",
        category_orders={"Month": month_order},
    )
    seasonality_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(seasonality_figure, width="stretch")

with geography_tab:
    state_chart, region_chart = st.columns(2)

    states = (
        filtered["state"]
        .value_counts()
        .head(top_count)
        .sort_values()
        .rename_axis("State or Territory")
        .reset_index(name="Declaration Records")
    )
    state_figure = px.bar(
        states,
        x="Declaration Records",
        y="State or Territory",
        orientation="h",
        title=f"Top {top_count} States and Territories",
        text_auto=",",
    )
    state_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    state_chart.plotly_chart(state_figure, width="stretch")

    regions = (
        filtered["femaRegion"]
        .value_counts()
        .rename_axis("FEMA Region")
        .reset_index(name="Declaration Records")
    )
    region_order = sort_region_labels(regions["FEMA Region"].tolist())
    region_figure = px.bar(
        regions,
        x="FEMA Region",
        y="Declaration Records",
        title="Declaration Records by FEMA Region",
        text_auto=",",
        category_orders={"FEMA Region": region_order},
    )
    region_figure.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    region_chart.plotly_chart(region_figure, width="stretch")

    state_incident = (
        filtered.groupby(["state", "incidentType"])
        .size()
        .reset_index(name="Declaration Records")
        .sort_values("Declaration Records", ascending=False)
        .head(top_count)
    )
    st.subheader("Leading State and Incident-Type Combinations")
    st.dataframe(
        state_incident,
        width="stretch",
        hide_index=True,
    )

with data_tab:
    display_columns = [
        "disasterNumber",
        "declarationDate",
        "state",
        "femaRegion",
        "incidentType",
        "declarationTypeLabel",
        "declarationTitle",
        "designatedArea",
    ]
    display_columns = [column for column in display_columns if column in filtered.columns]
    display_data = filtered[display_columns].copy()

    st.caption(f"Showing {len(display_data):,} filtered declaration records.")
    st.dataframe(
        display_data,
        width="stretch",
        hide_index=True,
        column_config={
            "declarationDate": st.column_config.DateColumn(
                "Declaration Date",
                format="MM/DD/YYYY",
            ),
            "disasterNumber": st.column_config.NumberColumn(
                "Disaster Number",
                format="%d",
            ),
        },
    )

    st.download_button(
        "Download Filtered Data as CSV",
        data=display_data.to_csv(index=False).encode("utf-8"),
        file_name="fema_filtered_declarations.csv",
        mime="text/csv",
        width="stretch",
    )

with st.expander("Methodology and limitations"):
    st.markdown(
        """
        - The application uses FEMA OpenFEMA Disaster Declarations Summaries v2 data.
        - Dates, state codes, incident labels, declaration types, and FEMA region labels are standardized before analysis.
        - Dashboard totals count declaration records unless a metric explicitly says unique disaster numbers.
        - Declaration records are administrative records and do not directly measure disaster severity or total economic impact.
        - A public deployment first attempts to load the full live FEMA CSV and falls back to the repository sample only when the live source is unavailable.
        """
    )

st.caption(
    "Data source: FEMA OpenFEMA Disaster Declarations Summaries v2. "
    "This dashboard supports exploratory analysis and situational awareness."
)
