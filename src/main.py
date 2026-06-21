"""Application entry point."""

import os

import uvicorn

from src.config import settings


def main() -> None:
    port = int(os.environ.get("PORT", settings.port))
    reload = os.getenv("RAILWAY_ENVIRONMENT") is None

    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
