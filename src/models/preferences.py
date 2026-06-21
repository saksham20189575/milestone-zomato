from typing import Literal

from pydantic import BaseModel, Field, field_validator

Budget = Literal["low", "medium", "high"]


class UserPreferences(BaseModel):
    location: str = Field(min_length=1)
    budget: Budget
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    cuisine: str | None = None
    additional: str | None = None

    @field_validator("location", mode="before")
    @classmethod
    def strip_location(cls, value: object) -> str:
        if value is None:
            raise ValueError("Location is required")
        text = str(value).strip()
        if not text:
            raise ValueError("Location is required")
        return text

    @field_validator("budget", mode="before")
    @classmethod
    def normalize_budget(cls, value: object) -> str:
        if value is None:
            raise ValueError("Budget is required")
        budget = str(value).strip().lower()
        if budget not in {"low", "medium", "high"}:
            raise ValueError("Budget must be one of: low, medium, high")
        return budget

    @field_validator("cuisine", mode="before")
    @classmethod
    def normalize_cuisine(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text.title() if text else None

    @field_validator("additional", mode="before")
    @classmethod
    def normalize_additional(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
