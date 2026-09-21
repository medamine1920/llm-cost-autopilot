import time

from groq import AsyncGroq

from app.models.registry import ModelConfig
from app.providers.base import Provider, Response


class GroqProvider(Provider):

    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def send(self, prompt: str, config: ModelConfig) -> Response:
        start = time.perf_counter()

        completion = await self.client.chat.completions.create(
            model=config.model_id,
            messages=[{"role": "user", "content": prompt}],
        )

        latency_ms = int((time.perf_counter() - start) * 1000)

        # TODO: pull these from `completion` — inspect its shape first
        text = completion.choices[0].message.content              # the generated text
        input_tokens = completion.usage.prompt_tokens      # usage info
        output_tokens = completion.usage.completion_tokens 

        return Response(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=config.cost_for(input_tokens, output_tokens),
            model_id=config.model_id,
            provider="groq",
        )