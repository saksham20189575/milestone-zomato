from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    rank: int = Field(ge=1)
    name: str
    cuisine: str
    rating: float = Field(ge=0.0, le=5.0)
    estimated_cost: int
    explanation: str


class RecommendationMetadata(BaseModel):
    candidates_considered: int = Field(ge=0)
    filters_applied: dict[str, str | float | None]
    model: str
    warnings: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    summary: str | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    metadata: RecommendationMetadata
