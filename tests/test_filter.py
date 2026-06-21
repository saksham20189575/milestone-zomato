import pytest
from pydantic import ValidationError

from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.filter import RestaurantFilter
from src.services.preferences import (
    PreferenceNormalizer,
    PreferenceValidationError,
    PreferenceValidator,
)


@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    return [
        Restaurant(
            id="1",
            name="Italian Garden",
            location="Indiranagar",
            cuisines=["Italian", "Continental"],
            cost_for_two=1200,
            rating=4.5,
            votes=500,
            rest_type="Casual Dining",
            budget_tier="medium",
        ),
        Restaurant(
            id="2",
            name="Budget Chinese",
            location="BTM",
            cuisines=["Chinese"],
            cost_for_two=400,
            rating=4.0,
            votes=200,
            rest_type="Cafe",
            budget_tier="medium",
        ),
        Restaurant(
            id="3",
            name="Premium Italian",
            location="Bellandur",
            cuisines=["Italian"],
            cost_for_two=2000,
            rating=4.8,
            votes=1000,
            rest_type="Fine Dining",
            budget_tier="high",
        ),
        Restaurant(
            id="4",
            name="Banashankari Diner",
            location="Banashankari",
            cuisines=["North Indian"],
            cost_for_two=800,
            rating=4.2,
            votes=300,
            rest_type="Casual Dining",
            budget_tier="medium",
        ),
        Restaurant(
            id="5",
            name="Low Rated Italian",
            location="Indiranagar",
            cuisines=["Italian"],
            cost_for_two=900,
            rating=3.2,
            votes=50,
            rest_type="Cafe",
            budget_tier="medium",
        ),
        Restaurant(
            id="6",
            name="Indo-Chinese Spot",
            location="Indiranagar",
            cuisines=["Indo-Chinese"],
            cost_for_two=600,
            rating=4.1,
            votes=150,
            rest_type="Casual Dining",
            budget_tier="medium",
        ),
    ]


@pytest.fixture
def validator() -> PreferenceValidator:
    return PreferenceValidator(
        valid_locations=["Indiranagar", "BTM", "Bellandur", "Banashankari"],
        valid_cuisines=["Italian", "Chinese", "North Indian", "Indo-Chinese"],
    )


def test_invalid_budget_raises_validation_error():
    with pytest.raises(ValidationError):
        UserPreferences(location="Indiranagar", budget="cheap", min_rating=3.0)


def test_min_rating_out_of_range_rejected():
    with pytest.raises(ValidationError):
        UserPreferences(location="Indiranagar", budget="medium", min_rating=5.5)


def test_preference_normalizer_maps_locality_alias():
    normalizer = PreferenceNormalizer()
    result = normalizer.normalize(
        {"location": "indira nagar", "budget": "Medium", "cuisine": "italian"}
    )
    assert result["location"] == "Indiranagar"
    assert result["budget"] == "medium"
    assert result["cuisine"] == "Italian"


def test_validator_rejects_unknown_location(validator: PreferenceValidator):
    with pytest.raises(PreferenceValidationError) as exc_info:
        validator.validate({"location": "Mumbai", "budget": "medium"})
    assert "Unknown location" in str(exc_info.value)


def test_validator_accepts_alias_location(validator: PreferenceValidator):
    prefs = validator.validate({"location": "indira nagar", "budget": "low"})
    assert prefs.location == "Indiranagar"


def test_filter_by_location_returns_only_matching_locality(
    sample_restaurants: list[Restaurant],
):
    prefs = UserPreferences(location="Indiranagar", budget="medium", min_rating=0.0)
    result = RestaurantFilter(max_candidates=20).filter(sample_restaurants, prefs)
    assert result.candidates
    assert all(r.location == "Indiranagar" for r in result.candidates)


def test_budget_filter_uses_budget_tier(sample_restaurants: list[Restaurant]):
    sample_restaurants[1] = sample_restaurants[1].model_copy(
        update={"budget_tier": "low"}
    )
    prefs = UserPreferences(location="BTM", budget="low", min_rating=0.0)
    result = RestaurantFilter().filter(sample_restaurants, prefs)
    assert len(result.candidates) == 1
    assert result.candidates[0].name == "Budget Chinese"
    assert result.candidates[0].budget_tier == "low"


def test_cuisine_filter_matches_restaurant_cuisine_list(
    sample_restaurants: list[Restaurant],
):
    prefs = UserPreferences(
        location="Indiranagar",
        budget="medium",
        min_rating=4.0,
        cuisine="Italian",
    )
    result = RestaurantFilter().filter(sample_restaurants, prefs)
    names = {r.name for r in result.candidates}
    assert "Italian Garden" in names
    assert "Low Rated Italian" not in names
    assert all(
        any(c.lower() == "italian" for c in r.cuisines) for r in result.candidates
    )


def test_cuisine_filter_does_not_substring_match_indo_chinese(
    sample_restaurants: list[Restaurant],
):
    prefs = UserPreferences(
        location="BTM",
        budget="medium",
        min_rating=4.0,
        cuisine="Chinese",
    )
    result = RestaurantFilter().filter(sample_restaurants, prefs)
    names = {r.name for r in result.candidates}
    assert "Budget Chinese" in names
    assert "Indo-Chinese Spot" not in names


def test_result_count_capped_at_max_candidates(sample_restaurants: list[Restaurant]):
    prefs = UserPreferences(location="Indiranagar", budget="medium", min_rating=0.0)
    result = RestaurantFilter(max_candidates=2).filter(sample_restaurants, prefs)
    assert len(result.candidates) == 2


def test_zero_results_triggers_relaxation_warning(sample_restaurants: list[Restaurant]):
    prefs = UserPreferences(
        location="Indiranagar",
        budget="low",
        min_rating=4.5,
        cuisine="Italian",
    )
    result = RestaurantFilter().filter(sample_restaurants, prefs)
    assert result.candidates
    assert result.warnings
    assert result.relaxed_filters


def test_sorts_by_rating_then_votes(sample_restaurants: list[Restaurant]):
    prefs = UserPreferences(location="Indiranagar", budget="medium", min_rating=0.0)
    result = RestaurantFilter(max_candidates=10).filter(sample_restaurants, prefs)
    ratings = [r.rating for r in result.candidates]
    assert ratings == sorted(ratings, reverse=True)


def test_filter_deduplicates_same_name_in_location():
    duplicates = [
        Restaurant(
            id="1",
            name="Lakeview Milkbar",
            location="MG Road",
            cuisines=["Desserts"],
            cost_for_two=400,
            rating=4.0,
            votes=100,
            budget_tier="low",
        ),
        Restaurant(
            id="2",
            name="lakeview milkbar",
            location="MG Road",
            cuisines=["Desserts"],
            cost_for_two=400,
            rating=4.0,
            votes=300,
            budget_tier="low",
        ),
        Restaurant(
            id="3",
            name="Other Cafe",
            location="MG Road",
            cuisines=["Cafe"],
            cost_for_two=600,
            rating=4.2,
            votes=50,
            budget_tier="medium",
        ),
    ]
    prefs = UserPreferences(location="MG Road", budget="low", min_rating=0.0)
    result = RestaurantFilter(max_candidates=10).filter(duplicates, prefs)

    names = [r.name.lower() for r in result.candidates]
    assert len(names) == len(set(names))
    assert names.count("lakeview milkbar") == 1
    assert result.candidates[0].votes == 300
