"""FastAPI application entrypoint."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.chat import render as render_chat
from app.config import get_settings
from app.dashboard import render as render_dashboard
from app.providers.groq import GroqProvider
from app.providers.ollama import OllamaProvider
from app.router import BudgetTracker, CompletionRequest, CompletionResponse, Router
from app.store import RequestStore


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.version)

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    store = RequestStore(settings.db_path)
    budget = BudgetTracker(daily_limit_usd=settings.daily_budget_usd, store=store)
    router = Router(
        providers={
            "groq": GroqProvider(api_key=settings.groq_api_key),
            "ollama": OllamaProvider(base_url=settings.ollama_base_url),
        },
        budget=budget,
        store=store,
    )

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return render_chat(settings.app_name, settings.version)

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard(days: int = 7) -> str:
        return render_dashboard(store.stats(days=days), settings.app_name, settings.version)

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

    @app.get("/v1/stats")
    def stats(days: int = 7) -> dict:
        return store.stats(days=days)

    @app.get("/v1/budget")
    def budget_status() -> dict:
        return {
            "daily_limit_usd": budget.daily_limit_usd,
            "spent_today_usd": round(budget.spent, 6),
            "exhausted": budget.exhausted,
        }

    return app


app = create_app()