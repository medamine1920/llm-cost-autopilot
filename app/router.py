"""Routing: decide which tier a prompt needs, then call that model."""

import re
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.registry import REGISTRY, ROUTING
from app.providers.base import Provider, Response

CALC_WORDS = ("total", "after", "days", "percent", "%", "discount", "tax",
              "change", "cost", "price", "rounded", "sum", "how much")


def choose_tier(prompt: str) -> tuple[str, str]:
    """Rule-based brain (v1). Returns (tier, reason).

    Phase 2 evaluated a trained classifier against these rules; the rules matched
    it on accuracy and made fewer quality-risk errors, so they were retained.
    """
    text = prompt.lower()
    numbers = len(re.findall(r"\d+", prompt))
    comparisons = len(re.findall(r"\b(older|younger|before|after|taller|shorter) than\b", text))

    if "how many times" in text or "letter" in text:
        return "moderate", "letter counting (small model sees tokens, not letters)"
    if numbers >= 3:
        return "moderate", f"{numbers} numbers in prompt: arithmetic risk"
    if any(w in text for w in CALC_WORDS) and numbers >= 1:
        return "moderate", "calculation keywords with numbers"
    if comparisons >= 3:
        return "moderate", f"{comparisons}-step comparison chain"
    if any(w in text for w in ("sentiment", "review", "mixed")):
        return "moderate", "nuanced sentiment judgment"
    if len(prompt) > 400:
        return "moderate", "long prompt"
    return "simple", "no complexity signals detected"


class CompletionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class CompletionResponse(BaseModel):
    text: str
    model: str
    tier: str
    cost_usd: float
    latency_ms: int
    routing_reason: str


class BudgetTracker:
    """Tracks paid spend per UTC day. In-memory v1: resets on restart."""

    def __init__(self, daily_limit_usd: float):
        self.daily_limit_usd = daily_limit_usd
        self._day = self._today()
        self._spent = 0.0

    @staticmethod
    def _today():
        return datetime.now(timezone.utc).date()

    def _roll_day(self) -> None:
        today = self._today()
        if today != self._day:
            self._day, self._spent = today, 0.0

    @property
    def spent(self) -> float:
        self._roll_day()
        return self._spent

    @property
    def exhausted(self) -> bool:
        return self.spent >= self.daily_limit_usd

    def record(self, cost_usd: float) -> None:
        self._roll_day()
        self._spent += cost_usd


class Router:
    def __init__(self, providers: dict[str, Provider], budget: BudgetTracker):
        self.providers = providers
        self.budget = budget

    async def _send(self, model_key: str, prompt: str) -> Response:
        config = REGISTRY[model_key]
        return await self.providers[config.provider].send(prompt, config)

    async def complete(self, prompt: str) -> CompletionResponse:
        tier, reason = choose_tier(prompt)

        if tier != "simple" and self.budget.exhausted:
            reason = f"daily budget cap reached, downgraded to simple tier (was: {reason})"
            tier = "simple"

        model_key = ROUTING.tiers[tier]

        try:
            response = await self._send(model_key, prompt)
        except Exception as exc:
            if model_key == ROUTING.fallback or self.budget.exhausted:
                raise          # no paid fallback once the budget is spent
            reason += f" | fallback: {model_key} failed ({type(exc).__name__})"
            model_key = ROUTING.fallback
            response = await self._send(model_key, prompt)

        self.budget.record(response.cost_usd)

        return CompletionResponse(
            text=response.text,
            model=model_key,
            tier=tier,
            cost_usd=round(response.cost_usd, 8),
            latency_ms=response.latency_ms,
            routing_reason=reason,
        )