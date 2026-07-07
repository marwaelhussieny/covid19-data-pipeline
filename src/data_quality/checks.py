"""
Data quality gate for the cleaned COVID-19 table, using pandera.

This runs *between* transform and load: if the clean table fails these
checks, the pipeline should fail loudly rather than silently loading bad
data into the warehouse. In the Airflow DAG this is its own task so a
failure shows up as a distinct, alertable step rather than being buried
inside a generic "load" task.
"""
from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema

clean_covid_schema = DataFrameSchema(
    {
        "province_state": Column(str, nullable=False),
        "country_region": Column(str, nullable=False),
        "latitude": Column(float, Check.in_range(-90, 90), nullable=True),
        "longitude": Column(float, Check.in_range(-180, 180), nullable=True),
        "cumulative_confirmed": Column(int, Check.ge(0), nullable=True, coerce=True),
        "cumulative_deaths": Column(int, Check.ge(0), nullable=True, coerce=True),
        "new_confirmed": Column(float, nullable=True),
        "new_deaths": Column(float, nullable=True),
        "is_data_correction": Column(bool, nullable=False),
        "date": Column(object, nullable=False),
    },
    checks=[
        # deaths should never exceed confirmed cases for the same location/day
        Check(
            lambda df: (df["cumulative_deaths"] <= df["cumulative_confirmed"]).mean() > 0.99,
            error="More than 1% of rows have cumulative_deaths > cumulative_confirmed",
        )
    ],
    strict=False,
    coerce=True,
)


class DataQualityError(Exception):
    """Raised when the clean table fails validation."""


def validate_clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """Validate df against the schema. Returns the (possibly coerced) df or raises."""
    try:
        return clean_covid_schema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as exc:
        raise DataQualityError(
            f"Data quality validation failed with {len(exc.failure_cases)} failing rows:\n"
            f"{exc.failure_cases.head(20)}"
        ) from exc
