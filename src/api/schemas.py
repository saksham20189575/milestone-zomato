"""Request and response schemas for the REST API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.models.recommendation import Recommendation, RecommendationMetadata

Budget = Literal["low", "medium", "high"]


class RecommendRequest(BaseModel):
    """User preferences submitted to POST /api/v1/recommend."""

    model_config = ConfigDict(populate_by_name=True)

    location: str = Field(min_length=1, examples=["Bangalore"])
    budget: Budget = Field(examples=["medium"])
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0, examples=[4.0])
    cuisine: str | None = Field(default=None, examples=["Italian"])
    additional_preferences: str | None = Field(
        default=None,
        alias="additional",
        examples=["family-friendly, quick service"],
    )

    def to_preference_dict(self) -> dict[str, str | float | None]:
        return {
            "location": self.location,
            "budget": self.budget,
            "min_rating": self.min_rating,
            "cuisine": self.cuisine,
            "additional": self.additional_preferences,
        }


class RecommendResponse(BaseModel):
    summary: str | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    metadata: RecommendationMetadata


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "starting"]
    dataset_loaded: bool
    restaurant_count: int = 0
    message: str | None = None


class LocationsResponse(BaseModel):
    locations: list[str]


class CuisinesResponse(BaseModel):
    cuisines: list[str]


class ValidationErrorDetail(BaseModel):
    message: str
    suggestions: list[str] = Field(default_factory=list)
