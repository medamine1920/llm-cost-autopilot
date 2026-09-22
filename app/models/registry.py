"""Model registry loaded from models.yaml, validated at startup."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

from app.config import get_settings

DEFAULT_CONFIG = Path(__file__).with_name("models.yaml")
REQUIRED_TIERS = ("simple", "moderate")


class QualityTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model_id: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    avg_latency_ms: int
    quality_tier: QualityTier

    def cost_for(self, input_tokens: int, output_tokens: int) -> float:
        """Cost in USD for one request."""
        return (
            input_tokens * self.cost_per_1m_input
            + output_tokens * self.cost_per_1m_output
        ) / 1_000_000


@dataclass(frozen=True)
class RoutingConfig:
    tiers: dict[str, str]
    fallback: str
    escalation: str | None


def load_config(path: Path) -> tuple[dict[str, ModelConfig], RoutingConfig]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    models = {}
    for key, spec in raw["models"].items():
        spec = dict(spec)
        spec["quality_tier"] = QualityTier(spec["quality_tier"])
        models[key] = ModelConfig(**spec)

    r = raw["routing"]
    routing = RoutingConfig(
        tiers=dict(r["tiers"]),
        fallback=r["fallback"],
        escalation=r.get("escalation"),
    )

    # Fail fast at startup instead of on the first request
    missing = [t for t in REQUIRED_TIERS if t not in routing.tiers]
    if missing:
        raise ValueError(f"{path}: routing.tiers is missing {missing}")
    referenced = list(routing.tiers.values()) + [routing.fallback]
    if routing.escalation:
        referenced.append(routing.escalation)
    unknown = [m for m in referenced if m not in models]
    if unknown:
        raise ValueError(f"{path}: routing references unknown models {unknown}")

    return models, routing


_path = Path(get_settings().models_config_path or DEFAULT_CONFIG)
REGISTRY, ROUTING = load_config(_path)