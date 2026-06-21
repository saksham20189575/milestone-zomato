"""Load the Zomato dataset from cache or Hugging Face."""

import json
import logging
import os
import tempfile
import time
from io import StringIO
from pathlib import Path

import httpx
import pandas as pd

from src.config import settings
from src.data.preprocessor import deduplicate_restaurants, preprocess_dataframe
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Columns required by the preprocessor from the public CSV export.
CSV_COLUMNS = [
    "name",
    "location",
    "listed_in(city)",
    "rate",
    "votes",
    "rest_type",
    "cuisines",
    "approx_cost(for two people)",
]


def _download_raw_dataframe() -> pd.DataFrame:
    last_error: Exception | None = None

    for attempt in range(MAX_DOWNLOAD_RETRIES):
        temp_path: str | None = None
        try:
            logger.info(
                "Downloading dataset CSV from Hugging Face: %s (attempt %d/%d)",
                settings.hf_dataset_csv_url,
                attempt + 1,
                MAX_DOWNLOAD_RETRIES,
            )
            with httpx.stream(
                "GET",
                settings.hf_dataset_csv_url,
                follow_redirects=True,
                timeout=httpx.Timeout(120.0, connect=30.0),
            ) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    suffix=".csv",
                    delete=False,
                ) as temp_file:
                    temp_path = temp_file.name
                    for chunk in response.iter_bytes():
                        temp_file.write(chunk)

            df = pd.read_csv(
                temp_path,
                usecols=lambda column: column in CSV_COLUMNS,
                dtype=str,
                keep_default_na=False,
            )
            logger.info("Downloaded %d raw rows from CSV", len(df))
            return df
        except Exception as exc:
            last_error = exc
            if attempt >= MAX_DOWNLOAD_RETRIES - 1:
                break
            backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "Dataset download failed (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                MAX_DOWNLOAD_RETRIES,
                backoff,
                exc,
            )
            time.sleep(backoff)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    raise RuntimeError(
        f"Failed to download dataset after {MAX_DOWNLOAD_RETRIES} attempts: {last_error}"
    ) from last_error


def _restaurants_to_dataframe(restaurants: list[Restaurant]) -> pd.DataFrame:
    records = [
        {
            "id": r.id,
            "name": r.name,
            "location": r.location,
            "cuisines": json.dumps(r.cuisines),
            "cost_for_two": r.cost_for_two,
            "rating": r.rating,
            "votes": r.votes,
            "rest_type": r.rest_type,
            "budget_tier": r.budget_tier,
        }
        for r in restaurants
    ]
    return pd.DataFrame(records)


def _dataframe_to_restaurants(df: pd.DataFrame) -> list[Restaurant]:
    restaurants: list[Restaurant] = []
    for row in df.to_dict(orient="records"):
        cuisines = row["cuisines"]
        if isinstance(cuisines, str):
            cuisines = json.loads(cuisines)

        rest_type = row.get("rest_type")
        if rest_type is None or (isinstance(rest_type, float) and pd.isna(rest_type)):
            rest_type = None
        else:
            rest_type = str(rest_type)

        restaurants.append(
            Restaurant(
                id=str(row["id"]),
                name=row["name"],
                location=row["location"],
                cuisines=cuisines,
                cost_for_two=int(row["cost_for_two"]),
                rating=float(row["rating"]),
                votes=int(row["votes"]),
                rest_type=rest_type,
                budget_tier=row["budget_tier"],
            )
        )
    return restaurants


def _save_cache(restaurants: list[Restaurant], cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    _restaurants_to_dataframe(restaurants).to_parquet(cache_path, index=False)
    logger.info("Cached %d restaurants to %s", len(restaurants), cache_path)


def _load_cache(cache_path: Path) -> list[Restaurant]:
    logger.info("Loading restaurants from cache: %s", cache_path)
    df = pd.read_parquet(cache_path)
    return _dataframe_to_restaurants(df)


def load_restaurants(*, force_refresh: bool = False) -> list[Restaurant]:
    """Load preprocessed restaurants from cache or Hugging Face."""
    cache_path = settings.data_cache_path
    refreshed = False

    if not force_refresh and cache_path.exists():
        restaurants = _load_cache(cache_path)
    else:
        raw_df = _download_raw_dataframe()
        restaurants = preprocess_dataframe(raw_df)
        refreshed = True

    deduped = deduplicate_restaurants(restaurants)
    if len(deduped) != len(restaurants):
        logger.info(
            "Deduplicated %d restaurants to %d unique name+location entries",
            len(restaurants),
            len(deduped),
        )
        restaurants = deduped
        _save_cache(restaurants, cache_path)
    elif refreshed or not cache_path.exists():
        _save_cache(restaurants, cache_path)

    return restaurants


def load_restaurants_from_csv(csv_text: str) -> list[Restaurant]:
    """Load restaurants from CSV text. Useful for tests."""
    df = pd.read_csv(
        StringIO(csv_text),
        usecols=lambda column: column in CSV_COLUMNS,
        dtype=str,
        keep_default_na=False,
    )
    return preprocess_dataframe(df)
