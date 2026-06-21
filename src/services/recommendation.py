"""Orchestrate filtering, LLM ranking, parsing, and enrichment."""

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

from src.config import settings
from src.data.preprocessor import restaurant_identity_key
from src.data.loader import load_restaurants
from src.data.repository import RestaurantRepository
from src.models.preferences import UserPreferences
from src.models.recommendation import (
    Recommendation,
    RecommendationMetadata,
    RecommendationResponse,
)
from src.models.restaurant import Restaurant
from src.services.filter import FilterResult, RestaurantFilter
from src.services.llm_client import LLMClient, LLMClientError
from src.services.preferences import PreferenceValidator
from src.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

JSON_FENCE_PATTERN = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)

FALLBACK_EXPLANATION = (
    "Ranked by rating and popularity based on your filters. "
    "AI-generated explanation is unavailable."
)
GENERIC_EXPLANATION = "Matches your preferences for {location} and {budget} budget."


class LLMRecommendationItem(BaseModel):
    id: str
    rank: int = Field(ge=1)
    explanation: str = ""


class LLMRecommendationResult(BaseModel):
    summary: str | None = None
    recommendations: list[LLMRecommendationItem] = Field(default_factory=list)


class ResponseParseError(ValueError):
    """Raised when LLM output cannot be parsed into the expected schema."""


class ResponseParser:
    def parse(self, content: str) -> LLMRecommendationResult:
        cleaned = self._strip_markdown_fences(content.strip())
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ResponseParseError(f"Invalid JSON from LLM: {exc}") from exc

        if not isinstance(payload, dict):
            raise ResponseParseError("LLM response must be a JSON object")

        if "recommendations" not in payload:
            raise ResponseParseError("LLM response missing 'recommendations' key")

        try:
            return LLMRecommendationResult.model_validate(payload)
        except ValidationError as exc:
            raise ResponseParseError(f"LLM response schema invalid: {exc}") from exc

    @staticmethod
    def _strip_markdown_fences(content: str) -> str:
        match = JSON_FENCE_PATTERN.match(content)
        if match:
            return match.group(1).strip()
        return content


class RecommendationEnricher:
    def __init__(self, top_k: int | None = None) -> None:
        self._top_k = top_k or settings.top_k_recommendations

    def enrich(
        self,
        parsed: LLMRecommendationResult,
        candidates: list[Restaurant],
        preferences: UserPreferences,
    ) -> tuple[list[Recommendation], str | None]:
        candidate_map = {r.id: r for r in candidates}
        seen_ids: set[str] = set()
        seen_restaurants: set[tuple[str, str]] = set()
        enriched: list[tuple[int, Recommendation]] = []

        sorted_items = sorted(
            parsed.recommendations,
            key=lambda item: (item.rank, item.id),
        )

        for index, item in enumerate(sorted_items):
            restaurant = candidate_map.get(item.id)
            if restaurant is None:
                logger.warning("LLM returned unknown restaurant id: %s", item.id)
                continue
            if item.id in seen_ids:
                continue

            identity = restaurant_identity_key(restaurant)
            if identity in seen_restaurants:
                continue

            seen_ids.add(item.id)
            seen_restaurants.add(identity)
            rank = item.rank if item.rank > 0 else index + 1
            enriched.append(
                (
                    rank,
                    self._to_recommendation(
                        restaurant,
                        rank=rank,
                        explanation=item.explanation,
                        preferences=preferences,
                    ),
                )
            )

        enriched.sort(key=lambda pair: pair[0])
        recommendations = [rec for _, rec in enriched][: self._top_k]

        if len(recommendations) < self._top_k:
            recommendations = self._fill_from_heuristic(
                recommendations,
                candidates,
                preferences,
                seen_ids,
                seen_restaurants,
            )

        recommendations = recommendations[: self._top_k]
        recommendations = [
            rec.model_copy(update={"rank": index + 1})
            for index, rec in enumerate(recommendations)
        ]
        return recommendations, parsed.summary

    def build_fallback(
        self,
        candidates: list[Restaurant],
        preferences: UserPreferences,
    ) -> list[Recommendation]:
        ranked = sorted(
            candidates,
            key=lambda r: (-r.rating, -r.votes, r.name.lower(), r.id),
        )
        recommendations: list[Recommendation] = []
        seen_restaurants: set[tuple[str, str]] = set()

        for restaurant in ranked:
            identity = restaurant_identity_key(restaurant)
            if identity in seen_restaurants:
                continue
            seen_restaurants.add(identity)
            recommendations.append(
                self._to_recommendation(
                    restaurant,
                    rank=len(recommendations) + 1,
                    explanation=FALLBACK_EXPLANATION,
                    preferences=preferences,
                )
            )
            if len(recommendations) >= self._top_k:
                break

        return recommendations

    def _fill_from_heuristic(
        self,
        current: list[Recommendation],
        candidates: list[Restaurant],
        preferences: UserPreferences,
        included_ids: set[str],
        included_restaurants: set[tuple[str, str]],
    ) -> list[Recommendation]:
        remaining = [
            r
            for r in sorted(
                candidates,
                key=lambda r: (-r.rating, -r.votes, r.name.lower(), r.id),
            )
            if r.id not in included_ids
            and restaurant_identity_key(r) not in included_restaurants
        ]

        filled = list(current)
        next_rank = len(filled) + 1
        for restaurant in remaining:
            if len(filled) >= self._top_k:
                break
            filled.append(
                self._to_recommendation(
                    restaurant,
                    rank=next_rank,
                    explanation=FALLBACK_EXPLANATION,
                    preferences=preferences,
                )
            )
            next_rank += 1
            included_ids.add(restaurant.id)
            included_restaurants.add(restaurant_identity_key(restaurant))

        return filled

    def _to_recommendation(
        self,
        restaurant: Restaurant,
        *,
        rank: int,
        explanation: str,
        preferences: UserPreferences,
    ) -> Recommendation:
        text = explanation.strip()
        if not text:
            text = GENERIC_EXPLANATION.format(
                location=preferences.location,
                budget=preferences.budget,
            )

        return Recommendation(
            rank=rank,
            name=restaurant.name,
            cuisine=", ".join(restaurant.cuisines),
            rating=restaurant.rating,
            estimated_cost=restaurant.cost_for_two,
            explanation=text,
        )


class RecommendationService:
    def __init__(
        self,
        *,
        repository: RestaurantRepository | None = None,
        preference_validator: PreferenceValidator | None = None,
        restaurant_filter: RestaurantFilter | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
        response_parser: ResponseParser | None = None,
        enricher: RecommendationEnricher | None = None,
    ) -> None:
        self._repository = repository
        self._preference_validator = preference_validator
        self._filter = restaurant_filter or RestaurantFilter()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_client = llm_client or LLMClient()
        self._parser = response_parser or ResponseParser()
        self._enricher = enricher or RecommendationEnricher()

    def recommend(self, preferences: UserPreferences) -> RecommendationResponse:
        repository = self._get_repository()
        validated = self._validate_preferences(preferences, repository)
        filter_result = self._filter.filter(repository.get_all(), validated)

        if not filter_result.candidates:
            return self._empty_response(filter_result)

        return self._recommend_from_candidates(validated, filter_result)

    def recommend_from_candidates(
        self,
        preferences: UserPreferences,
        filter_result: FilterResult,
    ) -> RecommendationResponse:
        """Rank pre-filtered candidates (used by tests and internal pipeline)."""
        if not filter_result.candidates:
            return self._empty_response(filter_result)
        return self._recommend_from_candidates(preferences, filter_result)

    def _recommend_from_candidates(
        self,
        preferences: UserPreferences,
        filter_result: FilterResult,
    ) -> RecommendationResponse:
        candidates = filter_result.candidates
        system_prompt, user_prompt = self._prompt_builder.build(
            preferences,
            candidates,
        )

        parsed: LLMRecommendationResult | None = None
        used_fallback = False

        try:
            content = self._llm_client.complete(system_prompt, user_prompt)
            parsed = self._parser.parse(content)
        except (LLMClientError, ResponseParseError) as exc:
            logger.warning("LLM call or parse failed, retrying at lower temperature: %s", exc)
            try:
                content = self._llm_client.complete(
                    system_prompt,
                    user_prompt,
                    temperature=0.1,
                )
                parsed = self._parser.parse(content)
            except (LLMClientError, ResponseParseError) as retry_exc:
                logger.warning("LLM retry failed, using fallback ranking: %s", retry_exc)
                used_fallback = True

        if used_fallback or parsed is None:
            recommendations = self._enricher.build_fallback(candidates, preferences)
            summary = (
                "Showing top-rated matches from your filtered results. "
                "AI ranking was unavailable."
            )
        else:
            recommendations, summary = self._enricher.enrich(
                parsed,
                candidates,
                preferences,
            )

        return RecommendationResponse(
            summary=summary,
            recommendations=recommendations,
            metadata=RecommendationMetadata(
                candidates_considered=len(candidates),
                filters_applied=filter_result.filters_applied,
                model=self._llm_client.model,
                warnings=filter_result.warnings,
            ),
        )

    def _get_repository(self) -> RestaurantRepository:
        if self._repository is not None:
            return self._repository
        restaurants = load_restaurants()
        self._repository = RestaurantRepository(restaurants)
        return self._repository

    def _validate_preferences(
        self,
        preferences: UserPreferences,
        repository: RestaurantRepository,
    ) -> UserPreferences:
        if self._preference_validator is not None:
            return self._preference_validator.validate(preferences.model_dump())

        validator = PreferenceValidator(
            valid_locations=repository.get_locations(),
            valid_cuisines=repository.get_cuisines(),
        )
        return validator.validate(preferences.model_dump())

    @staticmethod
    def _empty_response(filter_result: FilterResult) -> RecommendationResponse:
        return RecommendationResponse(
            summary="No restaurants matched your filters. Try broadening your search.",
            recommendations=[],
            metadata=RecommendationMetadata(
                candidates_considered=0,
                filters_applied=filter_result.filters_applied,
                model=settings.groq_model,
                warnings=filter_result.warnings,
            ),
        )
