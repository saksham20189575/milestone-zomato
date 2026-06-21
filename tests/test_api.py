"""API integration tests with TestClient and mocked LLM."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.data.repository import RestaurantRepository
from src.models.restaurant import Restaurant
from src.services.llm_client import LLMClientError
from src.services.preferences import PreferenceValidator
from src.services.recommendation import RecommendationService

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_restaurants.json"


@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    raw = json.loads(FIXTURE_PATH.read_text())
    return [Restaurant.model_validate(item) for item in raw]


@pytest.fixture
def mock_llm_response() -> str:
    return json.dumps(
        {
            "summary": "Great Italian picks in Indiranagar.",
            "recommendations": [
                {"id": "1", "rank": 1, "explanation": "Best Italian option in the area."},
                {"id": "10", "rank": 2, "explanation": "Excellent pizza and pasta."},
                {"id": "2", "rank": 3, "explanation": "Affordable backup option."},
            ],
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
        del system_prompt, user_prompt, temperature
        if isinstance(self._responses, Exception):
            raise self._responses
        if self._call_index >= len(self._responses):
            raise LLMClientError("No more mock responses")
        content = self._responses[self._call_index]
        self._call_index += 1
        return content


@pytest.fixture
def test_client(sample_restaurants: list[Restaurant], mock_llm_response: str) -> TestClient:
    repository = RestaurantRepository(sample_restaurants)
    service = RecommendationService(
        repository=repository,
        preference_validator=PreferenceValidator(
            valid_locations=repository.get_locations(),
            valid_cuisines=repository.get_cuisines(),
        ),
        llm_client=MockLLMClient([mock_llm_response]),
    )
    app = create_app(repository=repository, recommendation_service=service)
    return TestClient(app)


@pytest.fixture
def client_no_api_key(sample_restaurants: list[Restaurant], mock_llm_response: str) -> TestClient:
    repository = RestaurantRepository(sample_restaurants)
    service = RecommendationService(
        repository=repository,
        preference_validator=PreferenceValidator(
            valid_locations=repository.get_locations(),
            valid_cuisines=repository.get_cuisines(),
        ),
        llm_client=MockLLMClient([mock_llm_response]),
    )
    app = create_app(repository=repository, recommendation_service=service)
    return TestClient(app)


def test_health_returns_ok(test_client: TestClient):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["dataset_loaded"] is True
    assert data["restaurant_count"] == 10


def test_health_degraded_when_dataset_not_loaded():
    app = create_app(skip_dataset_load=True)
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["dataset_loaded"] is False


def test_locations_returns_sorted_list(test_client: TestClient):
    response = test_client.get("/api/v1/locations")
    assert response.status_code == 200
    locations = response.json()["locations"]
    assert locations == sorted(locations)
    assert "Indiranagar" in locations


def test_cuisines_returns_sorted_list(test_client: TestClient):
    response = test_client.get("/api/v1/cuisines")
    assert response.status_code == 200
    cuisines = response.json()["cuisines"]
    assert cuisines == sorted(cuisines)
    assert "Italian" in cuisines


def test_locations_returns_503_when_dataset_unavailable():
    app = create_app(skip_dataset_load=True)
    client = TestClient(app)
    response = client.get("/api/v1/locations")
    assert response.status_code == 503


def test_recommend_returns_recommendations(
    test_client: TestClient,
    mock_llm_response: str,
):
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.groq_api_key = "test-key"

        response = test_client.post(
            "/api/v1/recommend",
            json={
                "location": "Indiranagar",
                "budget": "medium",
                "cuisine": "Italian",
                "min_rating": 4.0,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) >= 1
    assert data["summary"] == "Great Italian picks in Indiranagar."
    assert data["metadata"]["candidates_considered"] > 0
    assert data["metadata"]["filters_applied"]["location"] == "Indiranagar"
    assert data["metadata"]["model"] == "test-model"
    assert "warnings" in data["metadata"]

    first = data["recommendations"][0]
    assert first["rank"] == 1
    assert first["name"] == "Italian Garden"
    assert "explanation" in first
    assert "rating" in first
    assert "estimated_cost" in first


def test_recommend_accepts_additional_preferences_alias(test_client: TestClient):
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.groq_api_key = "test-key"

        response = test_client.post(
            "/api/v1/recommend",
            json={
                "location": "Indiranagar",
                "budget": "medium",
                "min_rating": 4.0,
                "additional_preferences": "family-friendly",
            },
        )

    assert response.status_code == 200


def test_recommend_unknown_location_returns_422(test_client: TestClient):
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.groq_api_key = "test-key"

        response = test_client.post(
            "/api/v1/recommend",
            json={
                "location": "Nonexistent City",
                "budget": "medium",
                "min_rating": 4.0,
            },
        )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Unknown location" in detail["message"]
    assert isinstance(detail["suggestions"], list)


def test_recommend_invalid_budget_returns_422(test_client: TestClient):
    response = test_client.post(
        "/api/v1/recommend",
        json={
            "location": "Indiranagar",
            "budget": "luxury",
            "min_rating": 4.0,
        },
    )
    assert response.status_code == 422


def test_recommend_missing_groq_api_key_returns_503(test_client: TestClient):
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.groq_api_key = ""

        response = test_client.post(
            "/api/v1/recommend",
            json={
                "location": "Indiranagar",
                "budget": "medium",
                "min_rating": 4.0,
            },
        )

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_recommend_fallback_when_llm_fails(sample_restaurants: list[Restaurant]):
    repository = RestaurantRepository(sample_restaurants)
    service = RecommendationService(
        repository=repository,
        preference_validator=PreferenceValidator(
            valid_locations=repository.get_locations(),
            valid_cuisines=repository.get_cuisines(),
        ),
        llm_client=MockLLMClient(LLMClientError("API down")),
    )
    app = create_app(repository=repository, recommendation_service=service)
    client = TestClient(app)

    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.groq_api_key = "test-key"

        response = client.post(
            "/api/v1/recommend",
            json={
                "location": "Indiranagar",
                "budget": "medium",
                "min_rating": 4.0,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) >= 1
    assert "unavailable" in data["summary"].lower()


def test_cors_allows_frontend_origin(test_client: TestClient):
    response = test_client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_openapi_docs_available(test_client: TestClient):
    response = test_client.get("/docs")
    assert response.status_code == 200
