import pytest

from app.models.registry import ROUTING, REGISTRY, load_config


def test_bundled_config_is_valid():
    assert ROUTING.tiers["simple"] in REGISTRY
    assert ROUTING.tiers["moderate"] in REGISTRY


def test_unknown_model_in_routing_fails_fast(tmp_path):
    bad = tmp_path / "models.yaml"
    bad.write_text(
        """
models:
  m1: {provider: groq, model_id: x, cost_per_1m_input: 0, cost_per_1m_output: 0,
       avg_latency_ms: 1, quality_tier: low}
routing:
  tiers: {simple: m1, moderate: does-not-exist}
  fallback: m1
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown models"):
        load_config(bad)