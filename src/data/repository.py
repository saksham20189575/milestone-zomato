"""In-memory query interface over preprocessed restaurants."""

from src.models.restaurant import Restaurant


class RestaurantRepository:
    def __init__(self, restaurants: list[Restaurant]) -> None:
        self._restaurants = restaurants

    def get_all(self) -> list[Restaurant]:
        return list(self._restaurants)

    def get_locations(self) -> list[str]:
        locations = {restaurant.location for restaurant in self._restaurants if restaurant.location}
        return sorted(locations)

    def get_cuisines(self) -> list[str]:
        cuisines: set[str] = set()
        for restaurant in self._restaurants:
            cuisines.update(restaurant.cuisines)
        return sorted(cuisines)

    def __len__(self) -> int:
        return len(self._restaurants)
