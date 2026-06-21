"""API route handlers."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.dependencies import (
    ensure_groq_configured,
    get_recommendation_service,
    get_repository,
)
from src.api.schemas import (
    CuisinesResponse,
    HealthResponse,
    LocationsResponse,
    RecommendRequest,
    RecommendResponse,
    ValidationErrorDetail,
)
from src.data.repository import RestaurantRepository
from src.models.preferences import UserPreferences
from src.services.preferences import PreferenceValidationError
from src.services.recommendation import RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    dataset_loaded = getattr(request.app.state, "dataset_loaded", False)
    if not dataset_loaded:
        return HealthResponse(
            status="degraded",
            dataset_loaded=False,
            restaurant_count=0,
            message=getattr(request.app.state, "load_error", "Dataset not loaded"),
        )

    repository: RestaurantRepository = request.app.state.repository
    return HealthResponse(
        status="ok",
        dataset_loaded=True,
        restaurant_count=len(repository),
    )


@router.get("/locations", response_model=LocationsResponse)
def list_locations(
    repository: RestaurantRepository = Depends(get_repository),
) -> LocationsResponse:
    return LocationsResponse(locations=repository.get_locations())


@router.get("/cuisines", response_model=CuisinesResponse)
def list_cuisines(
    repository: RestaurantRepository = Depends(get_repository),
) -> CuisinesResponse:
    return CuisinesResponse(cuisines=repository.get_cuisines())


@router.post(
    "/recommend",
    response_model=RecommendResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ValidationErrorDetail},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
    },
)
def recommend(
    body: RecommendRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendResponse:
    ensure_groq_configured()

    try:
        preferences = UserPreferences.model_validate(body.to_preference_dict())
        response = service.recommend(preferences)
    except PreferenceValidationError as exc:
        logger.info("Preference validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ValidationErrorDetail(
                message=str(exc),
                suggestions=exc.suggestions,
            ).model_dump(),
        ) from exc

    logger.info(
        "Recommendation request location=%s budget=%s cuisine=%s min_rating=%s → %d results",
        preferences.location,
        preferences.budget,
        preferences.cuisine,
        preferences.min_rating,
        len(response.recommendations),
    )

    return RecommendResponse.model_validate(response.model_dump())
