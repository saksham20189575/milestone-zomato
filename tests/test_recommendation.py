import json
from unittest.mock import MagicMock

import pytest

from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant
from src.services.filter import FilterResult, RestaurantFilter
from src.services.llm_client import LLMClient, LLMClientError
from src.services.recommendation import (
    FALLBACK_EXPLANATION,
    RecommendationEnricher,
    RecommendationService,
    ResponseParseError,
    ResponseParser,
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
            location="Indiranagar",
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
    ]


@pytest.fixture
def locality_preferences() -> UserPreferences:
    return UserPreferences(
        location="Indiranagar",
        budget="medium",
        min_rating=4.0,
    )


@pytest.fixture
def italian_preferences() -> UserPreferences:
    return UserPreferences(
        location="Indiranagar",
        budget="medium",
        min_rating=4.0,
        cuisine="Italian",
    )


def _llm_json_response(
    recommendations: list[dict],
    *,
    summary: str = "Great Italian picks in Indiranagar.",
) -> str:
    return json.dumps(
        {
            "summary": summary,
            "recommendations": recommendations,
        }
    )


class MockLLMClient:
    def __init__(self, responses: list[str] | Exception) -> None:
        self._responses = responses
        self._call_index = 0
        self.model = "test-model"

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float | None = None,
    ) -> str:
        if isinstance(self._responses, Exception):
            raise self._responses

        if self._call_index >= len(self._responses):
            raise LLMClientError("No more mock responses")

        content = self._responses[self._call_index]
        self._call_index += 1
        return content


def test_response_parser_accepts_valid_json():
    content = _llm_json_response(
        [{"id": "1", "rank": 1, "explanation": "Best Italian option."}]
    )
    parsed = ResponseParser().parse(content)
    assert parsed.summary == "Great Italian picks in Indiranagar."
    assert len(parsed.recommendations) == 1
    assert parsed.recommendations[0].id == "1"


def test_response_parser_strips_markdown_fences():
    inner = _llm_json_response(
        [{"id": "1", "rank": 1, "explanation": "Nice spot."}]
    )
    content = f"```json\n{inner}\n```"
    parsed = ResponseParser().parse(content)
    assert parsed.recommendations[0].id == "1"


def test_response_parser_rejects_invalid_schema():
    with pytest.raises(ResponseParseError):
        ResponseParser().parse(json.dumps({"items": []}))


def test_response_parser_rejects_malformed_json():
    with pytest.raises(ResponseParseError):
        ResponseParser().parse("{not valid json")


def test_enricher_uses_structured_data_not_llm_names(
    italian_preferences: UserPreferences,
    sample_restaurants: list[Restaurant],
):
    from src.services.recommendation import LLMRecommendationResult, LLMRecommendationItem

    parsed = LLMRecommendationResult(
        summary="Summary",
        recommendations=[
            LLMRecommendationItem(
                id="1",
                rank=1,
                explanation="Perfect Italian fit.",
            )
        ],
    )
    candidates = [r for r in sample_restaurants if r.location == "Indiranagar"]
    recommendations, summary = RecommendationEnricher(top_k=1).enrich(
        parsed,
        candidates,
        italian_preferences,
    )

    assert summary == "Summary"
    assert len(recommendations) == 1
    assert recommendations[0].name == "Italian Garden"
    assert recommendations[0].cuisine == "Italian, Continental"
    assert recommendations[0].rating == 4.5
    assert recommendations[0].estimated_cost == 1200
    assert recommendations[0].explanation == "Perfect Italian fit."


def test_enricher_drops_unknown_ids(
    italian_preferences: UserPreferences,
    sample_restaurants: list[Restaurant],
):
    from src.services.recommendation import LLMRecommendationItem, LLMRecommendationResult

    parsed = LLMRecommendationResult(
        recommendations=[
            LLMRecommendationItem(id="999", rank=1, explanation="Fake."),
            LLMRecommendationItem(id="1", rank=2, explanation="Real."),
        ]
    )
    candidates = [r for r in sample_restaurants if r.location == "Indiranagar"]
    recommendations, _ = RecommendationEnricher(top_k=1).enrich(
        parsed,
        candidates,
        italian_preferences,
    )

    assert len(recommendations) == 1
    assert recommendations[0].name == "Italian Garden"


def test_enricher_deduplicates_same_restaurant_name(
    italian_preferences: UserPreferences,
):
    from src.services.recommendation import LLMRecommendationItem, LLMRecommendationResult

    candidates = [
        Restaurant(
            id="1",
            name="Italian Garden",
            location="Indiranagar",
            cuisines=["Italian"],
            cost_for_two=1200,
            rating=4.5,
            votes=500,
            budget_tier="medium",
        ),
        Restaurant(
            id="2",
            name="italian garden",
            location="Indiranagar",
            cuisines=["Italian"],
            cost_for_two=1200,
            rating=4.5,
            votes=100,
            budget_tier="medium",
        ),
    ]
    parsed = LLMRecommendationResult(
        recommendations=[
            LLMRecommendationItem(id="1", rank=1, explanation="First."),
            LLMRecommendationItem(id="2", rank=2, explanation="Duplicate."),
        ]
    )
    recommendations, _ = RecommendationEnricher(top_k=5).enrich(
        parsed,
        candidates,
        italian_preferences,
    )

    assert len(recommendations) == 1
    assert recommendations[0].name == "Italian Garden"


def test_enricher_fallback_ranks_by_rating(
    locality_preferences: UserPreferences,
    sample_restaurants: list[Restaurant],
):
    candidates = [r for r in sample_restaurants if r.location == "Indiranagar"]
    recommendations = RecommendationEnricher(top_k=2).build_fallback(
        candidates,
        locality_preferences,
    )

    assert len(recommendations) == 2
    assert recommendations[0].name == "Italian Garden"
    assert recommendations[0].rank == 1
    assert recommendations[0].explanation == FALLBACK_EXPLANATION


def test_recommendation_service_integration_with_mock_llm(
    locality_preferences: UserPreferences,
    sample_restaurants: list[Restaurant],
):
    filter_result = RestaurantFilter(max_candidates=10).filter(
        sample_restaurants,
        locality_preferences,
    )
    llm_response = _llm_json_response(
        [
            {"id": "1", "rank": 1, "explanation": "Great Italian and continental menu."},
            {"id": "2", "rank": 2, "explanation": "Affordable Chinese option."},
        ]
    )
    service = RecommendationService(
        llm_client=MockLLMClient([llm_response]),
        enricher=RecommendationEnricher(top_k=2),
    )

    response = service.recommend_from_candidates(
        locality_preferences,
        filter_result,
    )

    assert len(response.recommendations) == 2
    assert response.summary == "Great Italian picks in Indiranagar."
    assert response.metadata.candidates_considered == len(filter_result.candidates)
    assert response.metadata.filters_applied["location"] == "Indiranagar"
    assert response.metadata.model == "test-model"
    assert response.recommendations[0].name == "Italian Garden"
    assert response.recommendations[1].name == "Budget Chinese"


def test_recommendation_service_fallback_when_llm_fails(
    locality_preferences: UserPreferences,
    sample_restaurants: list[Restaurant],
):
    filter_result = RestaurantFilter(max_candidates=10).filter(
        sample_restaurants,
        locality_preferences,
    )
    service = RecommendationService(
        llm_client=MockLLMClient(LLMClientError("API down")),
        enricher=RecommendationEnricher(top_k=2),
    )

    response = service.recommend_from_candidates(
        locality_preferences,
        filter_result,
    )

    assert len(response.recommendations) == 2
    assert response.summary is not None
    assert "unavailable" in response.summary.lower()
    assert all(
        r.explanation == FALLBACK_EXPLANATION for r in response.recommendations
    )


def test_recommendation_service_retries_on_invalid_json_then_fallback(
    locality_preferences: UserPreferences,
    sample_restaurants: list[Restaurant],
):
    filter_result = RestaurantFilter(max_candidates=10).filter(
        sample_restaurants,
        locality_preferences,
    )
    service = RecommendationService(
        llm_client=MockLLMClient(["not-json", "{also bad"]),
        enricher=RecommendationEnricher(top_k=2),
    )

    response = service.recommend_from_candidates(
        locality_preferences,
        filter_result,
    )

    assert len(response.recommendations) == 2
    assert response.recommendations[0].explanation == FALLBACK_EXPLANATION


def test_recommendation_service_empty_candidates(
    locality_preferences: UserPreferences,
):
    empty_result = FilterResult(
        candidates=[],
        filters_applied={
            "location": locality_preferences.location,
            "budget": locality_preferences.budget,
            "min_rating": locality_preferences.min_rating,
            "cuisine": locality_preferences.cuisine,
        },
    )
    service = RecommendationService(llm_client=MockLLMClient([]))

    response = service.recommend_from_candidates(
        locality_preferences,
        empty_result,
    )

    assert response.recommendations == []
    assert response.metadata.candidates_considered == 0


def test_llm_client_requires_api_key():
    client = LLMClient(api_key="")
    with pytest.raises(LLMClientError, match="API key not configured"):
        client.complete("system", "user")


def test_llm_client_extracts_content_from_groq_response():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    mock_response.usage = None

    client = LLMClient(api_key="test-key", client=MagicMock())
    client._client.chat.completions.create.return_value = mock_response

    content = client.complete("system", "user")
    assert content == '{"ok": true}'
    client._client.chat.completions.create.assert_called_once()
    call_kwargs = client._client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}
