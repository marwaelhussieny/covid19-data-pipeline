"""
Streamlit dashboard for the COVID-19 pipeline. Reads only from dbt marts
(never the raw schema) so the dashboard automatically reflects whatever
business logic lives in the dbt models.
"""
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="COVID-19 Pipeline Dashboard", layout="wide")


@st.cache_resource
def get_engine():
    url = os.environ.get("WAREHOUSE_URL", "postgresql://airflow:airflow@postgres:5432/covid")
    return create_engine(url)


@st.cache_data(ttl=3600)
def load_global_daily() -> pd.DataFrame:
    return pd.read_sql("select * from marts.fct_covid_global_daily order by report_date", get_engine())


@st.cache_data(ttl=3600)
def load_country_daily() -> pd.DataFrame:
    return pd.read_sql("select * from marts.fct_covid_country_daily order by report_date", get_engine())


st.title("COVID-19 Data Pipeline — Dashboard")
st.caption("Source: JHU CSSE · Modeled with dbt · Orchestrated with Airflow")

global_df = load_global_daily()
country_df = load_country_daily()

latest = global_df.iloc[-1]
col1, col2, col3, col4 = st.columns(4)
col1.metric("Global confirmed", f"{int(latest['global_cumulative_confirmed']):,}")
col2.metric("Global deaths", f"{int(latest['global_cumulative_deaths']):,}")
col3.metric("Countries reporting", int(latest["countries_reporting"]))
col4.metric("As of", str(latest["report_date"]))

st.subheader("Global daily new cases (7-day smoothed at country level)")
fig = px.line(global_df, x="report_date", y="global_new_confirmed", labels={"global_new_confirmed": "New confirmed cases"})
st.plotly_chart(fig, use_container_width=True)

st.subheader("Compare countries")
countries = sorted(country_df["country_region"].unique())
selected = st.multiselect("Countries", countries, default=["United States", "United Kingdom", "France"] if "United States" in countries else countries[:3])

if selected:
    filtered = country_df[country_df["country_region"].isin(selected)]
    fig2 = px.line(
        filtered,
        x="report_date",
        y="new_confirmed_7day_avg",
        color="country_region",
        labels={"new_confirmed_7day_avg": "New confirmed cases (7-day avg)"},
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Case fatality rate (%) — latest reported day")
    latest_by_country = filtered.sort_values("report_date").groupby("country_region").tail(1)
    fig3 = px.bar(latest_by_country, x="country_region", y="case_fatality_rate_pct")
    st.plotly_chart(fig3, use_container_width=True)

with st.expander("Data quality notes"):
    corrections = country_df[country_df["had_data_correction"]]
    st.write(
        f"{corrections['country_region'].nunique()} countries have at least one day flagged as a "
        "retroactive data correction (negative day-over-day delta from the source)."
    )
    st.dataframe(corrections[["report_date", "country_region"]].head(20))
