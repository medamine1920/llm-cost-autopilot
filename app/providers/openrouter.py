"""OpenRouter provider: one API, many models (DeepSeek, Kimi, Qwen, ...)."""

import time

import httpx

from app.models.registry import ModelConfig
from app.providers.base import Provider, Response

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(Provider):

    def __init__(self, api_key: str):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "llm-cost-autopilot",
        }

    async def send(self, prompt: str, config: ModelConfig) -> Response:
        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers=self.headers,
                json={
                    "model": config.model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "seed": 42,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:                      # OpenRouter can return errors inside a 200
            raise RuntimeError(f"OpenRouter error: {data['error']}")

        latency_ms = int((time.perf_counter() - start) * 1000)

        text = data["choices"][0]["message"].get("content") or ""
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return Response(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=config.cost_for(input_tokens, output_tokens),
            model_id=config.model_id,
            provider="openrouter",
        )