"""FastAPI application factory, lifespan, and middleware."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router
from src.config import settings
from src.data.loader import load_restaurants
from src.data.repository import RestaurantRepository
from src.services.preferences import PreferenceValidationError
from src.services.recommendation import RecommendationService

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_app(
    *,
    repository: RestaurantRepository | None = None,
    recommendation_service: RecommendationService | None = None,
    skip_dataset_load: bool = False,
) -> FastAPI:
    """Create the FastAPI app. Pass a repository to skip startup dataset loading (tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _configure_logging()

        app.state.repository = None
        app.state.dataset_loaded = False
        app.state.load_error = None
        app.state.dataset_loading = False
        app.state.recommendation_service = recommendation_service

        if repository is not None:
            app.state.repository = repository
            app.state.dataset_loaded = True
            app.state.load_error = None
            app.state.recommendation_service = recommendation_service
            logger.info("Using injected repository with %d restaurants", len(repository))
        elif not skip_dataset_load:
            app.state.dataset_loading = True

            async def load_dataset_in_background() -> None:
                try:
                    restaurants = await asyncio.to_thread(load_restaurants)
                    app.state.repository = RestaurantRepository(restaurants)
                    app.state.dataset_loaded = True
                    app.state.load_error = None
                    logger.info("Loaded %d restaurants at startup", len(restaurants))
                except Exception as exc:
                    logger.error("Failed to load restaurant dataset: %s", exc)
                    app.state.repository = None
                    app.state.dataset_loaded = False
                    app.state.load_error = str(exc)
                finally:
                    app.state.dataset_loading = False

            asyncio.create_task(load_dataset_in_background())
        else:
            app.state.load_error = "Dataset loading skipped"

        yield

    app = FastAPI(
        title="Zomato AI Restaurant Recommendations",
        description="AI-powered restaurant recommendations using structured data and Groq LLM.",
        version="1.0.0",
        lifespan=lifespan,
    )

    if repository is not None:
        app.state.repository = repository
        app.state.dataset_loaded = True
        app.state.load_error = None
        app.state.recommendation_service = recommendation_service
    elif skip_dataset_load:
        app.state.repository = None
        app.state.dataset_loaded = False
        app.state.load_error = "Dataset loading skipped"
        app.state.recommendation_service = recommendation_service

    cors_kwargs: dict[str, Any] = {
        "allow_origins": settings.cors_origin_list,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    if settings.cors_origin_regex:
        cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "service": "Zomato AI Restaurant Recommendations",
            "health": "/api/v1/health",
            "docs": "/docs",
        }

    @app.exception_handler(PreferenceValidationError)
    async def preference_validation_handler(
        _request: Request,
        exc: PreferenceValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "message": str(exc),
                    "suggestions": exc.suggestions,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            errors.append(
                {
                    "field": field or "body",
                    "message": error.get("msg", "Invalid value"),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": {"message": "Validation failed", "errors": errors}},
        )

    app.include_router(router)
    return app


app = create_app()


def get_app_state(app: FastAPI) -> dict[str, Any]:
    return {
        "dataset_loaded": getattr(app.state, "dataset_loaded", False),
        "load_error": getattr(app.state, "load_error", None),
        "restaurant_count": len(app.state.repository)
        if getattr(app.state, "repository", None)
        else 0,
    }
