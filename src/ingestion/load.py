"""
Load the validated, clean COVID-19 table into the warehouse's raw schema.

dbt owns everything downstream of `raw.covid_daily` (staging + marts), so
this module's only job is a reliable, idempotent load of one table.
"""
from __future__ import annotations

import logging
import os

import pandas as pd
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

RAW_SCHEMA = "raw"
RAW_TABLE = "covid_daily"


def get_engine(connection_url: str | None = None):
    connection_url = connection_url or os.environ.get(
        "WAREHOUSE_URL", "postgresql://airflow:airflow@postgres:5432/covid"
    )
    return create_engine(connection_url)


def load_clean_table(df: pd.DataFrame, engine=None) -> int:
    """
    Replace the raw table with the freshly validated dataframe.

    Full-refresh (not incremental) is intentional here: JHU republishes the
    entire historical series on every run (including corrections to past
    days), so an append-only load would accumulate duplicates and drift
    from the source of truth.
    """
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
        df.to_sql(
            RAW_TABLE,
            con=conn,
            schema=RAW_SCHEMA,
            if_exists="replace",
            index=False,
            chunksize=5000,
        )
    logger.info("Loaded %d rows into %s.%s", len(df), RAW_SCHEMA, RAW_TABLE)
    return len(df)
