"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.providers.groq import GroqProvider
from app.providers.ollama import OllamaProvider
from app.router import BudgetTracker, CompletionRequest, CompletionResponse, Router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    budget = BudgetTracker(daily_limit_usd=settings.daily_budget_usd)
    router = Router(
        providers={
            "groq": GroqProvider(api_key=settings.groq_api_key),
            "ollama": OllamaProvider(base_url=settings.ollama_base_url),
        },
        budget=budget,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": settings.version,
            "environment": settings.app_env,
        }

    @app.post("/v1/completions", response_model=CompletionResponse)
    @limiter.limit(settings.rate_limit)
    async def completions(request: Request, body: CompletionRequest) -> CompletionResponse:
        try:
            return await router.complete(body.prompt)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"All providers failed: {type(exc).__name__}",
            ) from exc

    @app.get("/v1/budget")
    def budget_status() -> dict:
        return {
            "daily_limit_usd": budget.daily_limit_usd,
            "spent_today_usd": round(budget.spent, 6),
            "exhausted": budget.exhausted,
        }

    return app


app = create_app()