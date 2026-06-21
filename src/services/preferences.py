import difflib
from typing import Any

from src.data.preprocessor import LOCATION_ALIASES
from src.models.preferences import UserPreferences

ADDITIONAL_MAX_LENGTH = 500


class PreferenceValidationError(ValueError):
    def __init__(self, message: str, *, suggestions: list[str] | None = None) -> None:
        super().__init__(message)
        self.suggestions = suggestions or []


class PreferenceNormalizer:
    def normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(data)

        location = normalized.get("location")
        if location is not None:
            location = str(location).strip()
            normalized["location"] = LOCATION_ALIASES.get(location.lower(), location)

        budget = normalized.get("budget")
        if budget is not None:
            normalized["budget"] = str(budget).strip().lower()

        cuisine = normalized.get("cuisine")
        if cuisine is not None:
            cuisine = str(cuisine).strip()
            normalized["cuisine"] = cuisine.title() if cuisine else None

        additional = normalized.get("additional")
        if additional is not None:
            additional = str(additional).strip()
            if not additional:
                normalized["additional"] = None
            elif len(additional) > ADDITIONAL_MAX_LENGTH:
                normalized["additional"] = additional[:ADDITIONAL_MAX_LENGTH]
            else:
                normalized["additional"] = additional

        return normalized


class PreferenceValidator:
    def __init__(
        self,
        valid_locations: list[str],
        valid_cuisines: list[str] | None = None,
    ) -> None:
        self._valid_locations = valid_locations
        self._location_lookup = {loc.lower(): loc for loc in valid_locations}
        self._valid_cuisines = valid_cuisines or []
        self._cuisine_lookup = {c.lower(): c for c in self._valid_cuisines}
        self._normalizer = PreferenceNormalizer()

    def validate(self, data: dict[str, Any]) -> UserPreferences:
        normalized = self._normalizer.normalize(data)

        try:
            preferences = UserPreferences.model_validate(normalized)
        except Exception as exc:
            raise PreferenceValidationError(str(exc)) from exc

        preferences = preferences.model_copy(
            update={"location": self._validate_location(preferences.location)}
        )

        if preferences.cuisine is not None:
            preferences = preferences.model_copy(
                update={"cuisine": self._validate_cuisine(preferences.cuisine)}
            )

        return preferences

    def _validate_location(self, location: str) -> str:
        if not location.strip():
            raise PreferenceValidationError("Location is required")

        canonical = self._location_lookup.get(location.lower())
        if canonical:
            return canonical

        suggestions = difflib.get_close_matches(
            location,
            self._valid_locations,
            n=5,
            cutoff=0.5,
        )
        message = f"Unknown location: {location}"
        if suggestions:
            message += f". Did you mean: {', '.join(suggestions)}?"
        raise PreferenceValidationError(message, suggestions=suggestions)

    def _validate_cuisine(self, cuisine: str) -> str:
        canonical = self._cuisine_lookup.get(cuisine.lower())
        if canonical:
            return canonical

        suggestions = difflib.get_close_matches(
            cuisine,
            self._valid_cuisines,
            n=5,
            cutoff=0.6,
        )
        if suggestions:
            return suggestions[0]

        message = f"Unknown cuisine: {cuisine}"
        if suggestions:
            message += f". Did you mean: {', '.join(suggestions)}?"
        raise PreferenceValidationError(message, suggestions=suggestions)
