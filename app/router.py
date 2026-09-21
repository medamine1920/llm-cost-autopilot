"""Routing: decide which tier a prompt needs, then call that model."""

import re

from pydantic import BaseModel, Field

from app.models.registry import REGISTRY
from app.providers.base import Provider, Response

TIER_TO_MODEL = {
    "simple": "ollama-local",
    "moderate": "groq-20b",
}
FALLBACK_MODEL = "groq-20b"

CALC_WORDS = ("total", "after", "days", "percent", "%", "discount", "tax",
              "change", "cost", "price", "rounded", "sum", "how much")


def choose_tier(prompt: str) -> tuple[str, str]:
    """Rule-based v1 brain. Returns (tier, reason). Replaced by a classifier in Phase 2."""
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


class Router:
    def __init__(self, providers: dict[str, Provider]):
        self.providers = providers

    async def _send(self, model_key: str, prompt: str) -> Response:
        config = REGISTRY[model_key]
        return await self.providers[config.provider].send(prompt, config)

    async def complete(self, prompt: str) -> CompletionResponse:
        tier, reason = choose_tier(prompt)
        model_key = TIER_TO_MODEL[tier]

        try:
            response = await self._send(model_key, prompt)
        except Exception as exc:
            if model_key == FALLBACK_MODEL:
                raise
            reason += f" | fallback: {model_key} failed ({type(exc).__name__})"
            model_key = FALLBACK_MODEL
            response = await self._send(model_key, prompt)

        return CompletionResponse(
            text=response.text,
            model=model_key,
            tier=tier,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            routing_reason=reason,
        )