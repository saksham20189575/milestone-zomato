import pandas as pd
import pytest

from src.data.preprocessor import (
    deduplicate_restaurants,
    derive_budget_tier,
    normalize_location,
    parse_cost,
    parse_cuisines,
    parse_rating,
    preprocess_dataframe,
)
from src.models.restaurant import Restaurant


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "name": "Jalsa",
                "address": "942, Banashankari, Bangalore",
                "location": "Banashankari",
                "rate": "4.1/5",
                "votes": 775,
                "rest_type": "Casual Dining",
                "cuisines": "North Indian, Mughlai, Chinese",
                "approx_cost(for two people)": "800",
            },
            {
                "name": "Budget Bites",
                "address": "12, Kumaraswamy Layout",
                "location": "Kumaraswamy Layout",
                "rate": "3.5/5",
                "votes": 120,
                "rest_type": "Cafe",
                "cuisines": "Italian",
                "approx_cost(for two people)": "500",
            },
            {
                "name": "Premium Place",
                "address": "100, MG Road, Bengaluru",
                "location": "MG Road",
                "rate": "4.8/5",
                "votes": 2000,
                "rest_type": "Fine Dining",
                "cuisines": "Italian, Continental",
                "approx_cost(for two people)": "1,200",
            },
            {
                "name": "Invalid Rating",
                "address": "1, Delhi",
                "location": "Connaught Place",
                "rate": "NEW",
                "votes": 10,
                "rest_type": "Cafe",
                "cuisines": "Chinese",
                "approx_cost(for two people)": "600",
            },
            {
                "name": "",
                "address": "2, Bangalore",
                "location": "Indiranagar",
                "rate": "4.0/5",
                "votes": 5,
                "rest_type": "Cafe",
                "cuisines": "Cafe",
                "approx_cost(for two people)": "300",
            },
        ]
    )


def test_parse_cuisines_splits_and_normalizes():
    assert parse_cuisines("italian, Chinese, Italian") == ["Italian", "Chinese"]
    assert parse_cuisines("") == []
    assert parse_cuisines(None) == []


def test_parse_rating_handles_fraction_and_invalid():
    assert parse_rating("4.1/5") == 4.1
    assert parse_rating("NEW") is None
    assert parse_rating(None) is None
    assert parse_rating("6.5/5") == 5.0


def test_parse_cost_strips_commas():
    assert parse_cost("1,200") == 1200
    assert parse_cost("0") is None
    assert parse_cost(None) is None


def test_normalize_location_aliases():
    assert normalize_location("indira nagar") == "Indiranagar"
    assert normalize_location("Bellandur") == "Bellandur"
    assert normalize_location("  BTM  ") == "BTM"


def test_derive_budget_tier_boundaries():
    assert derive_budget_tier(500) == "low"
    assert derive_budget_tier(501) == "medium"
    assert derive_budget_tier(1500) == "medium"
    assert derive_budget_tier(1501) == "high"


def test_preprocess_dataframe_maps_canonical_schema(sample_raw_df: pd.DataFrame):
    restaurants = preprocess_dataframe(sample_raw_df)

    assert len(restaurants) == 3
    assert all(isinstance(r, Restaurant) for r in restaurants)

    jalsa = restaurants[0]
    assert jalsa.name == "Jalsa"
    assert jalsa.location == "Banashankari"
    assert jalsa.cuisines == ["North Indian", "Mughlai", "Chinese"]
    assert jalsa.cost_for_two == 800
    assert jalsa.rating == 4.1
    assert jalsa.budget_tier == "medium"
    assert jalsa.votes == 775
    assert jalsa.rest_type == "Casual Dining"

    budget_bites = restaurants[1]
    assert budget_bites.location == "Kumaraswamy Layout"
    assert budget_bites.cost_for_two == 500
    assert budget_bites.budget_tier == "low"

    premium = restaurants[2]
    assert premium.cost_for_two == 1200
    assert premium.budget_tier == "medium"
    assert premium.location == "MG Road"


def test_deduplicate_restaurants_keeps_best_record():
    duplicates = [
        Restaurant(
            id="1",
            name="Cafe Azzure",
            location="MG Road",
            cuisines=["Cafe"],
            cost_for_two=800,
            rating=4.3,
            votes=100,
            budget_tier="medium",
        ),
        Restaurant(
            id="2",
            name="cafe azzure",
            location="MG Road",
            cuisines=["Cafe"],
            cost_for_two=800,
            rating=4.3,
            votes=500,
            budget_tier="medium",
        ),
        Restaurant(
            id="3",
            name="Other Place",
            location="MG Road",
            cuisines=["Italian"],
            cost_for_two=1200,
            rating=4.5,
            votes=50,
            budget_tier="medium",
        ),
    ]

    deduped = deduplicate_restaurants(duplicates)

    assert len(deduped) == 2
    kept = next(r for r in deduped if r.name.lower() == "cafe azzure")
    assert kept.id == "2"
    assert kept.votes == 500


def test_deduplicate_restaurants_preserves_same_name_different_location():
    restaurants = [
        Restaurant(
            id="1",
            name="Truffles",
            location="MG Road",
            cuisines=["American"],
            cost_for_two=800,
            rating=4.2,
            votes=100,
            budget_tier="medium",
        ),
        Restaurant(
            id="2",
            name="Truffles",
            location="Indiranagar",
            cuisines=["American"],
            cost_for_two=800,
            rating=4.4,
            votes=200,
            budget_tier="medium",
        ),
    ]

    deduped = deduplicate_restaurants(restaurants)

    assert len(deduped) == 2
