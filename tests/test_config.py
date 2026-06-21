from src.config import Settings


def test_default_groq_model():
    settings = Settings()
    assert settings.groq_model == "llama-3.3-70b-versatile"


def test_budget_thresholds_property():
    settings = Settings()
    assert settings.budget_thresholds == {"low_max": 500, "medium_max": 1500}
