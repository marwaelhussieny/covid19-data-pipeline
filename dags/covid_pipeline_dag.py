"""
Daily COVID-19 pipeline: extract JHU CSSE data, validate it, load it to the
warehouse's raw schema, then run dbt to build staging/mart models and dbt
tests to confirm they're correct.

Each stage is its own task so failures are isolated and visible in the
Airflow UI: a data-quality failure looks different from a dbt-test failure,
which looks different from a network failure during extraction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pendulum
from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

DBT_PROJECT_DIR = "/opt/airflow/dbt/covid_dbt"
RAW_DATA_DIR = Path("/opt/airflow/data/raw")


@dag(
    dag_id="covid_pipeline",
    schedule="@daily",
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=["covid", "portfolio"],
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)},
)
def covid_pipeline():

    @task
    def extract() -> dict:
        from ingestion.extract import download_all

        paths = download_all(RAW_DATA_DIR)
        return {k: str(v) for k, v in paths.items()}

    @task
    def transform_and_validate(paths: dict) -> str:
        from ingestion.transform import build_clean_table
        from data_quality.checks import validate_clean_table

        confirmed = pd.read_csv(paths["confirmed"])
        deaths = pd.read_csv(paths["deaths"])

        clean = build_clean_table(confirmed, deaths)
        validated = validate_clean_table(clean)  # raises DataQualityError on failure

        out_path = RAW_DATA_DIR.parent / "processed" / "covid_daily_clean.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        validated.to_parquet(out_path, index=False)
        return str(out_path)

    @task
    def load(parquet_path: str) -> int:
        from ingestion.load import load_clean_table

        df = pd.read_parquet(parquet_path)
        return load_clean_table(df)

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --target dev",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --target dev",
    )

    raw_paths = extract()
    clean_path = transform_and_validate(raw_paths)
    row_count = load(clean_path)
    row_count >> dbt_run >> dbt_test


covid_pipeline()
