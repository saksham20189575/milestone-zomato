from src.config import Settings


def test_default_groq_model():
    settings = Settings()
    assert settings.groq_model == "llama-3.3-70b-versatile"


def test_budget_thresholds_property():
    settings = Settings()
    assert settings.budget_thresholds == {"low_max": 500, "medium_max": 1500}


def test_cors_origin_regex_enabled_by_default():
    settings = Settings()
    assert settings.cors_allow_vercel_previews is True
    assert settings.cors_origin_regex == r"https://.*\.vercel\.app"
