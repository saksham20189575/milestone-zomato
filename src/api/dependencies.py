"""FastAPI dependencies for repository and service access."""

from fastapi import HTTPException, Request, status

from src.config import settings
from src.data.repository import RestaurantRepository
from src.services.preferences import PreferenceValidator
from src.services.recommendation import RecommendationService


def get_repository(request: Request) -> RestaurantRepository:
    if not getattr(request.app.state, "dataset_loaded", False):
        load_error = getattr(request.app.state, "load_error", None)
        detail = load_error or "Restaurant dataset is not available"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    repository = request.app.state.repository
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Restaurant dataset is not available",
        )
    return repository


def get_recommendation_service(request: Request) -> RecommendationService:
    repository = get_repository(request)
    service = getattr(request.app.state, "recommendation_service", None)
    if service is not None:
        return service

    return RecommendationService(
        repository=repository,
        preference_validator=PreferenceValidator(
            valid_locations=repository.get_locations(),
            valid_cuisines=repository.get_cuisines(),
        ),
    )


def ensure_groq_configured() -> None:
    if not settings.groq_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GROQ_API_KEY is not configured. Set it in your .env file.",
        )
