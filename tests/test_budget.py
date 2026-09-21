import asyncio

from app.providers.base import Provider, Response
from app.router import BudgetTracker, Router


class FakeProvider(Provider):
    def __init__(self, cost: float):
        self.cost = cost

    async def send(self, prompt, config):
        return Response(text="ok", input_tokens=1, output_tokens=1, latency_ms=1,
                        cost_usd=self.cost, model_id=config.model_id,
                        provider=config.provider)


def test_budget_cap_downgrades_to_free_tier():
    budget = BudgetTracker(daily_limit_usd=0.001)
    budget.record(0.002)                                  # already over budget
    router = Router({"groq": FakeProvider(0.01), "ollama": FakeProvider(0.0)}, budget)

    result = asyncio.run(router.complete("What is 12 + 34 + 56?"))   # normally "moderate"

    assert result.model == "ollama-local"
    assert "budget cap" in result.routing_reason