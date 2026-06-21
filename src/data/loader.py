"""Load the Zomato dataset from cache or Hugging Face."""

import json
import logging
import time
from pathlib import Path

import pandas as pd
from datasets import load_dataset

from src.config import settings
from src.data.preprocessor import deduplicate_restaurants, preprocess_dataframe
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0

# Hugging Face columns → internal names used by the preprocessor.
# Dataset: ManikaSaini/zomato-restaurant-recommendation
HF_COLUMNS = {
    "name": "name",
    "address": "address",
    "location": "locality",
    "rate": "rate",
    "votes": "votes",
    "rest_type": "rest_type",
    "cuisines": "cuisines",
    "approx_cost(for two people)": "approx_cost",
}


def _download_raw_dataframe() -> pd.DataFrame:
    last_error: Exception | None = None

    for attempt in range(MAX_DOWNLOAD_RETRIES):
        try:
            logger.info(
                "Downloading dataset from Hugging Face: %s (attempt %d/%d)",
                settings.hf_dataset_name,
                attempt + 1,
                MAX_DOWNLOAD_RETRIES,
            )
            dataset = load_dataset(settings.hf_dataset_name, split="train")
            df = dataset.to_pandas()
            logger.info("Downloaded %d raw rows", len(df))
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
