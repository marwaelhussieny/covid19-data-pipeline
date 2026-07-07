import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ingestion.transform import (  # noqa: E402
    wide_to_long,
    clean_locations,
    compute_daily_new,
    build_clean_table,
)


@pytest.fixture
def raw_confirmed():
    return pd.DataFrame(
        {
            "Province/State": [None, None],
            "Country/Region": ["US", "Korea, South"],
            "Lat": [37.0, 36.0],
            "Long": [-95.0, 128.0],
            "1/22/20": [1, 0],
            "1/23/20": [3, 1],
            "1/24/20": [5, 2],
        }
    )


@pytest.fixture
def raw_deaths():
    return pd.DataFrame(
        {
            "Province/State": [None, None],
            "Country/Region": ["US", "Korea, South"],
            "Lat": [37.0, 36.0],
            "Long": [-95.0, 128.0],
            "1/22/20": [0, 0],
            "1/23/20": [0, 0],
            "1/24/20": [1, 0],
        }
    )


def test_wide_to_long_reshapes_dates(raw_confirmed):
    long_df = wide_to_long(raw_confirmed, "cumulative_confirmed")
    assert set(long_df["date"].dt.strftime("%Y-%m-%d")) == {"2020-01-22", "2020-01-23", "2020-01-24"}
    assert len(long_df) == 6  # 2 countries x 3 dates


def test_clean_locations_maps_country_names_and_fills_province(raw_confirmed):
    long_df = wide_to_long(raw_confirmed, "cumulative_confirmed")
    cleaned = clean_locations(long_df)
    assert set(cleaned["country_region"]) == {"United States", "South Korea"}
    assert (cleaned["province_state"] == "Unspecified").all()


def test_compute_daily_new_first_day_equals_cumulative():
    df = pd.DataFrame(
        {
            "country_region": ["A", "A"],
            "province_state": ["x", "x"],
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "cumulative_confirmed": [5, 8],
        }
    )
    result = compute_daily_new(df, "cumulative_confirmed", "new_confirmed")
    assert result.iloc[0]["new_confirmed"] == 5
    assert result.iloc[1]["new_confirmed"] == 3


def test_compute_daily_new_flags_negative_corrections():
    df = pd.DataFrame(
        {
            "country_region": ["A", "A"],
            "province_state": ["x", "x"],
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "cumulative_confirmed": [10, 7],  # retroactive correction downward
        }
    )
    result = compute_daily_new(df, "cumulative_confirmed", "new_confirmed")
    assert result.iloc[1]["is_data_correction"] == True  # noqa: E712


def test_build_clean_table_end_to_end(raw_confirmed, raw_deaths):
    clean = build_clean_table(raw_confirmed, raw_deaths)
    assert {"cumulative_confirmed", "cumulative_deaths", "new_confirmed", "new_deaths"}.issubset(
        clean.columns
    )
    assert len(clean) == 6
    assert clean["cumulative_deaths"].le(clean["cumulative_confirmed"]).all()
