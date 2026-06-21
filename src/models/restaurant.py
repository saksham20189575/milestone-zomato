from typing import Literal

from pydantic import BaseModel, Field

BudgetTier = Literal["low", "medium", "high"]


class Restaurant(BaseModel):
    id: str
    name: str
    location: str
    cuisines: list[str] = Field(default_factory=list)
    cost_for_two: int
    rating: float = Field(ge=0.0, le=5.0)
    votes: int = 0
    rest_type: str | None = None
    budget_tier: BudgetTier
