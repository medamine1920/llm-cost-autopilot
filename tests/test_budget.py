import asyncio

from app.providers.base import Provider, Response
from app.router import BudgetTracker, Router

class FakeStore:
    def __init__(self, spent: float = 0.0):
        self._spent = spent
        self.records = []

    def spent_today(self) -> float:
        return self._spent

    def record(self, **kwargs) -> None:
        self.records.append(kwargs)


def test_budget_cap_downgrades_to_cheap_tier():
    store = FakeStore(spent=0.002)                     # already over the limit
    budget = BudgetTracker(daily_limit_usd=0.001, store=store)
    router = Router({"groq": FakeProvider(0.01), "ollama": FakeProvider(0.0)}, budget, store)

    result = asyncio.run(router.complete("What is 12 + 34 + 56?"))

    assert result.model == "ollama-local"
    assert "budget cap" in result.routing_reason
    assert store.records, "request should have been logged"

class FakeProvider(Provider):
    def __init__(self, cost: float):
        self.cost = cost

    async def send(self, prompt, config):
        return Response(text="ok", input_tokens=1, output_tokens=1, latency_ms=1,
                        cost_usd=self.cost, model_id=config.model_id,
                        provider=config.provider)
