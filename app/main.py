"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Report API health."""

        return {"status": "ok",
                "version": settings.version,
                "environment": settings.app_env,}
    return app


app = create_app()
