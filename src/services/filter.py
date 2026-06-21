"""Deterministic restaurant filtering before LLM ranking."""

import logging
from typing import Literal

from pydantic import BaseModel, Field

from src.data.preprocessor import deduplicate_restaurants
from src.config import settings
from src.models.preferences import UserPreferences
from src.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

RelaxableFilter = Literal["cuisine", "budget", "min_rating"]


class FilterResult(BaseModel):
    candidates: list[Restaurant] = Field(default_factory=list)
    filters_applied: dict[str, str | float | None]
    warnings: list[str] = Field(default_factory=list)
    relaxed_filters: list[RelaxableFilter] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class RestaurantFilter:
    def __init__(self, max_candidates: int | None = None) -> None:
        self._max_candidates = max_candidates or settings.max_candidates_for_llm

    def filter(
        self,
        restaurants: list[Restaurant],
        preferences: UserPreferences,
    ) -> FilterResult:
        filters_applied: dict[str, str | float | None] = {
            "location": preferences.location,
            "budget": preferences.budget,
            "min_rating": preferences.min_rating,
            "cuisine": preferences.cuisine,
        }

        candidates = self._apply_filters(restaurants, preferences)
        warnings: list[str] = []
        relaxed: list[RelaxableFilter] = []

        if not candidates:
            candidates, relaxed, warnings = self._relax_constraints(
                restaurants,
                preferences,
            )

        candidates = self._sort_and_cap(candidates)

        logger.info(
            "Filtered %d restaurants to %d candidates (relaxed: %s)",
            len(restaurants),
            len(candidates),
            relaxed or "none",
        )

        return FilterResult(
            candidates=candidates,
            filters_applied=filters_applied,
            warnings=warnings,
            relaxed_filters=relaxed,
        )

    def _apply_filters(
        self,
        restaurants: list[Restaurant],
        preferences: UserPreferences,
        *,
        include_cuisine: bool = True,
        include_budget: bool = True,
        min_rating: float | None = None,
    ) -> list[Restaurant]:
        rating_threshold = preferences.min_rating if min_rating is None else min_rating
        result = restaurants

        result = [
            r for r in result if r.location.lower() == preferences.location.lower()
        ]

        if include_budget:
            result = [r for r in result if r.budget_tier == preferences.budget]

        result = [r for r in result if r.rating >= rating_threshold]

        if include_cuisine and preferences.cuisine:
            cuisine = preferences.cuisine.lower()
            result = [
                r
                for r in result
                if any(c.lower() == cuisine for c in r.cuisines)
            ]

        return result

    def _relax_constraints(
        self,
        restaurants: list[Restaurant],
        preferences: UserPreferences,
    ) -> tuple[list[Restaurant], list[RelaxableFilter], list[str]]:
        relaxed: list[RelaxableFilter] = []
        warnings: list[str] = []
        include_cuisine = True
        include_budget = True
        rating_threshold: float | None = None

        if preferences.cuisine:
            include_cuisine = False
            relaxed.append("cuisine")
            warnings.append(
                f"No restaurants matched cuisine '{preferences.cuisine}'. "
                "Showing results without cuisine filter."
            )
            candidates = self._apply_filters(
                restaurants,
                preferences,
                include_cuisine=include_cuisine,
                include_budget=include_budget,
            )
            if candidates:
                return candidates, relaxed, warnings

        include_budget = False
        relaxed.append("budget")
        warnings.append(
            f"No restaurants matched budget '{preferences.budget}'. "
            "Showing results across all budget tiers."
        )
        candidates = self._apply_filters(
            restaurants,
            preferences,
            include_cuisine=include_cuisine,
            include_budget=include_budget,
        )
        if candidates:
            return candidates, relaxed, warnings

        relaxed.append("min_rating")
        warnings.append(
            f"No restaurants matched minimum rating {preferences.min_rating}. "
            f"Showing all rated options in {preferences.location}."
        )
        candidates = self._apply_filters(
            restaurants,
            preferences,
            include_cuisine=include_cuisine,
            include_budget=include_budget,
            min_rating=0.0,
        )
        return candidates, relaxed, warnings

    def _sort_and_cap(self, restaurants: list[Restaurant]) -> list[Restaurant]:
        unique_restaurants = deduplicate_restaurants(restaurants)
        sorted_restaurants = sorted(
            unique_restaurants,
            key=lambda r: (-r.rating, -r.votes, r.name.lower(), r.id),
        )
        return sorted_restaurants[: self._max_candidates]
