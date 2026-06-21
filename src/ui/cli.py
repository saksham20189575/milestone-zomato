"""Interactive CLI for local development and testing."""

import json
import sys

from src.config import settings
from src.data.loader import load_restaurants
from src.data.repository import RestaurantRepository
from src.services.preferences import PreferenceValidationError, PreferenceValidator
from src.services.recommendation import RecommendationService


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def main() -> int:
    print("Zomato AI Restaurant Recommendations (CLI)\n")

    if not settings.groq_api_key.strip():
        print("Error: GROQ_API_KEY is not configured. Set it in your .env file.", file=sys.stderr)
        return 1

    print("Loading restaurant data...")
    repository = RestaurantRepository(load_restaurants())
    validator = PreferenceValidator(
        valid_locations=repository.get_locations(),
        valid_cuisines=repository.get_cuisines(),
    )
    service = RecommendationService(
        repository=repository,
        preference_validator=validator,
    )

    location = _prompt("Location")
    budget = _prompt("Budget (low/medium/high)", "medium")
    cuisine = _prompt("Cuisine (optional)")
    min_rating = _prompt("Minimum rating (0-5)", "0")
    additional = _prompt("Additional preferences (optional)")

    try:
        preferences = validator.validate(
            {
                "location": location,
                "budget": budget,
                "min_rating": float(min_rating),
                "cuisine": cuisine or None,
                "additional": additional or None,
            }
        )
    except (PreferenceValidationError, ValueError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 1

    print("\nFetching recommendations...\n")
    response = service.recommend(preferences)

    if response.summary:
        print(f"Summary: {response.summary}\n")

    if response.metadata.warnings:
        for warning in response.metadata.warnings:
            print(f"Warning: {warning}")
        print()

    if not response.recommendations:
        print("No recommendations found. Try broadening your filters.")
        return 0

    for rec in response.recommendations:
        print(f"#{rec.rank} {rec.name}")
        print(f"   {rec.cuisine} | Rating: {rec.rating} | Cost: ₹{rec.estimated_cost}")
        print(f"   {rec.explanation}\n")

    print(json.dumps(response.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
