"""
Extract raw COVID-19 time-series data from the JHU CSSE GitHub repository.

Source: https://github.com/CSSEGISandData/COVID-19
The upstream files are wide-format (one column per date), inconsistent on
Province/State (often empty), and contain occasional negative-correction
values in later dates. This module only handles *extraction* - it fetches
the raw CSVs and hands them off untouched. Cleaning/reshaping happens in
transform.py so that raw data is always preserved in the bronze/raw layer.
"""
from __future__ import annotations

import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"
    "csse_covid_19_data/csse_covid_19_time_series"
)

DATASETS = {
    "confirmed": "time_series_covid19_confirmed_global.csv",
    "deaths": "time_series_covid19_deaths_global.csv",
}


def download_dataset(name: str, dest_dir: Path) -> Path:
    """Download one of the known datasets ('confirmed' or 'deaths') to dest_dir."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset '{name}'. Expected one of {list(DATASETS)}")

    url = f"{BASE_URL}/{DATASETS[name]}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{name}_global_raw.csv"

    logger.info("Downloading %s -> %s", url, dest_path)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    dest_path.write_bytes(response.content)
    logger.info("Saved %d bytes to %s", len(response.content), dest_path)
    return dest_path


def download_all(dest_dir: Path) -> dict[str, Path]:
    """Download all known datasets. Returns a mapping of name -> local path."""
    return {name: download_dataset(name, dest_dir) for name in DATASETS}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
    download_all(raw_dir)
