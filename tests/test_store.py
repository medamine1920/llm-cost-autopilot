from app.store import RequestStore


def test_empty_store(tmp_path):
    store = RequestStore(str(tmp_path / "t.db"))
    assert store.spent_today() == 0.0
    assert store.stats()["requests"] == 0


def test_records_and_computes_savings(tmp_path):
    store = RequestStore(str(tmp_path / "t.db"))
    store.record(prompt="hi", tier="simple", model="ollama-local", routing_reason="r",
                 input_tokens=10, output_tokens=5, cost_usd=0.0,
                 baseline_cost_usd=0.002, latency_ms=100)
    store.record(prompt="hello", tier="moderate", model="groq-20b", routing_reason="r",
                 input_tokens=10, output_tokens=5, cost_usd=0.002,
                 baseline_cost_usd=0.002, latency_ms=50)

    stats = store.stats()
    assert stats["requests"] == 2
    assert stats["savings_pct"] == 50.0
    assert store.spent_today() == 0.002