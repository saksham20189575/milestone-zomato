import json

import pytest

from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.prompt_builder import SYSTEM_PROMPT, PromptBuilder


@pytest.fixture
def sample_candidates() -> list[Restaurant]:
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
            budget_tier="low",
        ),
    ]


@pytest.fixture
def sample_preferences() -> UserPreferences:
    return UserPreferences(
        location="Indiranagar",
        budget="medium",
        min_rating=4.0,
        cuisine="Italian",
        additional="family-friendly",
    )


def test_system_prompt_requires_json_and_candidate_only_ranking():
    assert "JSON" in SYSTEM_PROMPT
    assert "CANDIDATES" in SYSTEM_PROMPT


def test_build_includes_all_preference_fields(
    sample_preferences: UserPreferences,
    sample_candidates: list[Restaurant],
):
    system_prompt, user_prompt = PromptBuilder(top_k=5).build(
        sample_preferences,
        sample_candidates,
    )

    assert system_prompt == SYSTEM_PROMPT
    assert "[User Preferences]" in user_prompt
    assert "[Candidates]" in user_prompt
    assert "[Task]" in user_prompt

    prefs_start = user_prompt.index("[User Preferences]") + len("[User Preferences]\n")
    prefs_end = user_prompt.index("\n\n[Candidates]")
    prefs = json.loads(user_prompt[prefs_start:prefs_end])

    assert prefs["location"] == "Indiranagar"
    assert prefs["budget"] == "medium"
    assert prefs["min_rating"] == 4.0
    assert prefs["cuisine"] == "Italian"
    assert prefs["additional"] == "family-friendly"


def test_build_includes_all_candidates(
    sample_preferences: UserPreferences,
    sample_candidates: list[Restaurant],
):
    _, user_prompt = PromptBuilder().build(sample_preferences, sample_candidates)

    candidates_start = user_prompt.index("[Candidates]") + len("[Candidates]\n")
    candidates_end = user_prompt.index("\n\n[Task]")
    candidates = json.loads(user_prompt[candidates_start:candidates_end])

    assert len(candidates) == len(sample_candidates)
    assert {c["id"] for c in candidates} == {r.id for r in sample_candidates}
    for candidate, restaurant in zip(candidates, sample_candidates):
        assert candidate["name"] == restaurant.name
        assert candidate["cuisines"] == restaurant.cuisines
        assert candidate["cost_for_two"] == restaurant.cost_for_two
        assert candidate["rating"] == restaurant.rating


def test_task_uses_min_of_top_k_and_candidate_count(
    sample_preferences: UserPreferences,
    sample_candidates: list[Restaurant],
):
    _, user_prompt = PromptBuilder(top_k=10).build(
        sample_preferences,
        sample_candidates,
    )
    assert "Return the top 2 restaurant(s)" in user_prompt


def test_build_rejects_empty_candidates(sample_preferences: UserPreferences):
    with pytest.raises(ValueError, match="zero candidates"):
        PromptBuilder().build(sample_preferences, [])


def test_prompt_snapshot_structure(
    sample_preferences: UserPreferences,
    sample_candidates: list[Restaurant],
):
    """Regression guard for prompt section ordering and keys."""
    _, user_prompt = PromptBuilder(top_k=3).build(
        sample_preferences,
        sample_candidates,
    )

    expected_prefix = (
        "[User Preferences]\n"
        '{"location": "Indiranagar", "budget": "medium", "min_rating": 4.0, '
        '"cuisine": "Italian", "additional": "family-friendly"}\n'
        "\n"
        "[Candidates]\n"
    )
    assert user_prompt.startswith(expected_prefix)
    assert user_prompt.endswith(
        "Base explanations on the user's preferences and each restaurant's attributes."
    )
