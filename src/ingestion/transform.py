"""
Transform raw JHU CSSE wide-format COVID-19 CSVs into a clean, long-format
table ready to load into the warehouse's raw/staging schema.

Handles the messiness called out in the project brief:
- Wide format (one column per date) -> long format (one row per date)
- Inconsistent / missing Province-State -> filled with a sentinel
- Country naming inconsistencies (e.g. "US" vs "United States") -> mapped
  to a single canonical name
- Negative daily deltas (data-corrections from the source) -> flagged
  rather than silently dropped, so downstream consumers can decide
"""
from __future__ import annotations

import pandas as pd

# JHU uses a handful of country names that don't match common usage /
# other datasets we might join against later. Extend this mapping as needed.
COUNTRY_NAME_MAP = {
    "US": "United States",
    "Korea, South": "South Korea",
    "Congo (Kinshasa)": "DR Congo",
    "Congo (Brazzaville)": "Republic of the Congo",
    "Taiwan*": "Taiwan",
    "Burma": "Myanmar",
    "Cabo Verde": "Cape Verde",
}

ID_COLUMNS = ["Province/State", "Country/Region", "Lat", "Long"]


def wide_to_long(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
    """Melt a JHU wide-format frame into long format: one row per location/date."""
    date_columns = [c for c in df.columns if c not in ID_COLUMNS]

    long_df = df.melt(
        id_vars=ID_COLUMNS,
        value_vars=date_columns,
        var_name="date_raw",
        value_name=value_name,
    )

    long_df["date"] = pd.to_datetime(long_df["date_raw"], format="%m/%d/%y")
    long_df = long_df.drop(columns=["date_raw"])
    return long_df


def clean_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize country names and fill missing province/state."""
    df = df.copy()
    df["Country/Region"] = df["Country/Region"].replace(COUNTRY_NAME_MAP)
    df["Province/State"] = df["Province/State"].fillna("Unspecified")
    df = df.rename(
        columns={
            "Province/State": "province_state",
            "Country/Region": "country_region",
            "Lat": "latitude",
            "Long": "longitude",
        }
    )
    return df


def compute_daily_new(df: pd.DataFrame, cumulative_col: str, new_col: str) -> pd.DataFrame:
    """
    Convert cumulative counts into daily new counts per location, and flag
    negative deltas (JHU periodically issues retroactive corrections rather
    than true negative case counts).
    """
    df = df.sort_values(["country_region", "province_state", "date"]).copy()
    group_keys = ["country_region", "province_state"]

    df[new_col] = df.groupby(group_keys)[cumulative_col].diff()
    # first observation per location has no prior day to diff against;
    # treat its cumulative value as the day-one count.
    df[new_col] = df[new_col].fillna(df[cumulative_col])

    df["is_data_correction"] = df[new_col] < 0
    return df


def build_clean_table(confirmed_raw: pd.DataFrame, deaths_raw: pd.DataFrame) -> pd.DataFrame:
    """Full pipeline: raw wide CSVs in, one clean long table out."""
    confirmed_long = clean_locations(wide_to_long(confirmed_raw, "cumulative_confirmed"))
    deaths_long = clean_locations(wide_to_long(deaths_raw, "cumulative_deaths"))

    merged = confirmed_long.merge(
        deaths_long,
        on=["province_state", "country_region", "latitude", "longitude", "date"],
        how="outer",
    )

    merged = compute_daily_new(merged, "cumulative_confirmed", "new_confirmed")
    merged = compute_daily_new(merged, "cumulative_deaths", "new_deaths")

    merged["date"] = merged["date"].dt.date
    return merged.reset_index(drop=True)
