"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.providers.groq import GroqProvider
from app.providers.ollama import OllamaProvider
from app.router import CompletionRequest, CompletionResponse, Router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)

    router = Router(providers={
        "groq": GroqProvider(api_key=settings.groq_api_key),
        "ollama": OllamaProvider(base_url=settings.ollama_base_url),
    })

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": settings.version,
            "environment": settings.app_env,
        }

    @app.post("/v1/completions", response_model=CompletionResponse)
    async def completions(request: CompletionRequest) -> CompletionResponse:
        try:
            return await router.complete(request.prompt)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"All providers failed: {type(exc).__name__}",
            ) from exc

    return app


app = create_app()