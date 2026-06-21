from src.data.repository import RestaurantRepository
from src.models.restaurant import Restaurant


def _sample_restaurants() -> list[Restaurant]:
    return [
        Restaurant(
            id="1",
            name="A",
            location="Indiranagar",
            cuisines=["Italian", "Chinese"],
            cost_for_two=800,
            rating=4.2,
            votes=100,
            rest_type="Cafe",
            budget_tier="medium",
        ),
        Restaurant(
            id="2",
            name="B",
            location="Banashankari",
            cuisines=["North Indian"],
            cost_for_two=400,
            rating=3.8,
            votes=50,
            rest_type=None,
            budget_tier="low",
        ),
        Restaurant(
            id="3",
            name="C",
            location="Indiranagar",
            cuisines=["Chinese"],
            cost_for_two=1600,
            rating=4.5,
            votes=200,
            rest_type="Fine Dining",
            budget_tier="high",
        ),
    ]


def test_get_all_returns_copy():
    repo = RestaurantRepository(_sample_restaurants())
    all_restaurants = repo.get_all()
    assert len(all_restaurants) == 3
    all_restaurants.clear()
    assert len(repo.get_all()) == 3


def test_get_locations_sorted_unique():
    repo = RestaurantRepository(_sample_restaurants())
    assert repo.get_locations() == ["Banashankari", "Indiranagar"]


def test_get_cuisines_sorted_unique():
    repo = RestaurantRepository(_sample_restaurants())
    assert repo.get_cuisines() == ["Chinese", "Italian", "North Indian"]
