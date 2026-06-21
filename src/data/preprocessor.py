"""Normalize raw Zomato dataset rows into canonical Restaurant models."""

import logging
import re
from typing import Any

import pandas as pd

from src.config import settings
from src.models.restaurant import BudgetTier, Restaurant

logger = logging.getLogger(__name__)

# Common locality spelling variants for user input normalization.
LOCALITY_ALIASES: dict[str, str] = {
    "indira nagar": "Indiranagar",
    "indi rangar": "Indiranagar",
    "koramangala": "Koramangala 5th Block",
    "hsr layout": "HSR",
    "hsr": "HSR",
    "btm layout": "BTM",
    "btm": "BTM",
    "mg road": "MG Road",
    "electronic city": "Electronic City",
    "white field": "Whitefield",
    "marathahalli": "Marathahalli",
    "bellandur": "Bellandur",
    "jayanagar": "Jayanagar",
    "banashankari": "Banashankari",
}

# Backward-compatible alias used by preference normalization.
LOCATION_ALIASES = LOCALITY_ALIASES


def parse_cuisines(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [part.strip() for part in text.split(",")]
    seen: set[str] = set()
    cuisines: list[str] = []
    for part in parts:
        if not part:
            continue
        normalized = part.title()
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            cuisines.append(normalized)
    return cuisines


def parse_rating(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper()
    if not text or text == "NEW" or text == "-":
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    rating = float(match.group(1))
    if rating < 0.0:
        return 0.0
    if rating > 5.0:
        return 5.0
    return rating


def parse_cost(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = re.sub(r"[^\d]", "", str(value))
    if not text:
        return None
    cost = int(text)
    return cost if cost > 0 else None


def parse_votes(value: Any) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def normalize_location(locality: str) -> str:
    """Normalize a Bangalore locality name for consistent storage and lookup."""
    text = re.sub(r"\s+", " ", str(locality).strip())
    if not text:
        return text
    return LOCALITY_ALIASES.get(text.lower(), text)


def parse_locality(row: Any) -> str | None:
    """Read locality from the dataset `location` column, with fallbacks."""
    locality = row.get("location") if hasattr(row, "get") else None
    if locality is not None and not (isinstance(locality, float) and pd.isna(locality)):
        text = str(locality).strip()
        if text:
            return normalize_location(text)

    listed_in = row.get("listed_in(city)")
    if listed_in is not None and not (isinstance(listed_in, float) and pd.isna(listed_in)):
        text = str(listed_in).strip()
        if text:
            return normalize_location(text)

    return None


def restaurant_identity_key(restaurant: Restaurant) -> tuple[str, str]:
    """Normalized key for deduplicating the same venue within a locality."""
    return (restaurant.name.lower().strip(), restaurant.location.lower())


def _restaurant_quality_key(restaurant: Restaurant) -> tuple[float, float, str]:
    """Sort key where lower values represent higher-quality records."""
    return (-restaurant.rating, -restaurant.votes, restaurant.id)


def deduplicate_restaurants(restaurants: list[Restaurant]) -> list[Restaurant]:
    """Keep one record per name+location, preferring highest rating and votes."""
    best_by_key: dict[tuple[str, str], Restaurant] = {}

    for restaurant in restaurants:
        key = restaurant_identity_key(restaurant)
        existing = best_by_key.get(key)
        if existing is None or _restaurant_quality_key(restaurant) < _restaurant_quality_key(
            existing
        ):
            best_by_key[key] = restaurant

    return list(best_by_key.values())


def derive_budget_tier(cost_for_two: int) -> BudgetTier:
    low_max = settings.budget_low_max
    medium_max = settings.budget_medium_max
    if cost_for_two <= low_max:
        return "low"
    if cost_for_two <= medium_max:
        return "medium"
    return "high"


def preprocess_dataframe(df: pd.DataFrame) -> list[Restaurant]:
    """Transform raw Hugging Face DataFrame into validated Restaurant objects."""
    restaurants: list[Restaurant] = []
    dropped = 0

    for index, row in df.iterrows():
        name = str(row.get("name", "")).strip()
        if not name:
            dropped += 1
            continue

        rating = parse_rating(row.get("rate"))
        if rating is None:
            dropped += 1
            continue

        cost_for_two = parse_cost(row.get("approx_cost(for two people)"))
        if cost_for_two is None:
            dropped += 1
            continue

        locality = parse_locality(row)
        if locality is None:
            dropped += 1
            continue

        location = locality
        rest_type_value = row.get("rest_type")
        rest_type = (
            str(rest_type_value).strip()
            if rest_type_value is not None and not pd.isna(rest_type_value)
            else None
        )

        restaurants.append(
            Restaurant(
                id=str(index),
                name=name,
                location=location,
                cuisines=parse_cuisines(row.get("cuisines")),
                cost_for_two=cost_for_two,
                rating=rating,
                votes=parse_votes(row.get("votes")),
                rest_type=rest_type or None,
                budget_tier=derive_budget_tier(cost_for_two),
            )
        )

    before_dedup = len(restaurants)
    restaurants = deduplicate_restaurants(restaurants)
    deduped = before_dedup - len(restaurants)

    logger.info(
        "Preprocessed %d restaurants (%d rows dropped, %d duplicates merged)",
        len(restaurants),
        dropped,
        deduped,
    )
    return restaurants
