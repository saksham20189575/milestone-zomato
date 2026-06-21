"""Tests for dataset loading."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.data.loader import CSV_COLUMNS, load_restaurants, load_restaurants_from_csv

SAMPLE_CSV = """name,location,listed_in(city),rate,votes,rest_type,cuisines,approx_cost(for two people)
Jalsa,Banashankari,Bangalore,4.1/5,775,Casual Dining,"North Indian, Mughlai, Chinese",800
Budget Bites,Kumaraswamy Layout,Bangalore,3.5/5,120,Cafe,Italian,500
Invalid Rating,Connaught Place,Delhi,NEW,10,Cafe,Chinese,600
"""


def test_load_restaurants_from_csv_parses_rows():
    restaurants = load_restaurants_from_csv(SAMPLE_CSV)

    assert len(restaurants) == 2
    assert restaurants[0].name == "Jalsa"
    assert restaurants[1].name == "Budget Bites"


def test_load_restaurants_uses_cache(tmp_path: Path):
    cache_path = tmp_path / "restaurants.parquet"

    with patch("src.data.loader.settings") as mock_settings:
        mock_settings.data_cache_path = cache_path
        restaurants = load_restaurants_from_csv(SAMPLE_CSV)
        from src.data.loader import _save_cache

        _save_cache(restaurants, cache_path)

        with patch("src.data.loader._download_raw_dataframe") as mock_download:
            loaded = load_restaurants()
            mock_download.assert_not_called()

    assert len(loaded) == 2


def test_csv_columns_match_preprocessor_inputs():
    assert "location" in CSV_COLUMNS
    assert "approx_cost(for two people)" in CSV_COLUMNS
