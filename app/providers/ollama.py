import time

import httpx

from app.models.registry import ModelConfig
from app.providers.base import Provider, Response


class OllamaProvider(Provider):

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url

    async def send(self, prompt: str, config: ModelConfig) -> Response:
        start = time.perf_counter()

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": config.model_id, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()

        latency_ms = int((time.perf_counter() - start) * 1000)

        text = data["response"]
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return Response(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=config.cost_for(input_tokens, output_tokens),
            model_id=config.model_id,
            provider="ollama",
        )