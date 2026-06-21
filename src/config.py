from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = Field(default=0.3, ge=0.0, le=2.0)

    hf_dataset_name: str = "ManikaSaini/zomato-restaurant-recommendation"
    data_cache_path: Path = Path("data/restaurants.parquet")

    max_candidates_for_llm: int = Field(default=20, ge=1)
    top_k_recommendations: int = Field(default=5, ge=1)

    budget_low_max: int = Field(default=500, ge=0)
    budget_medium_max: int = Field(default=1500, ge=0)

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_allow_vercel_previews: bool = True

    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator("budget_medium_max")
    @classmethod
    def medium_must_exceed_low(cls, value: int, info) -> int:
        low_max = info.data.get("budget_low_max", 500)
        if value <= low_max:
            raise ValueError("budget_medium_max must be greater than budget_low_max")
        return value

    @property
    def budget_thresholds(self) -> dict[str, int]:
        return {
            "low_max": self.budget_low_max,
            "medium_max": self.budget_medium_max,
        }

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex(self) -> str | None:
        if self.cors_allow_vercel_previews:
            return r"https://.*\.vercel\.app"
        return None


settings = Settings()
