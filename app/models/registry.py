"""Model registry: available models, their costs, and quality tiers."""

from dataclasses import dataclass
from enum import Enum


class QualityTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ModelConfig:
    provider: str            # "groq" | "gemini" | "ollama"
    model_id: str            
    cost_per_1m_input: float
    cost_per_1m_output: float
    avg_latency_ms: int
    quality_tier: QualityTier

    def cost_for(self, input_tokens: int, output_tokens: int) -> float:
        """Cost in USD for one request."""
        return (
            input_tokens * self.cost_per_1m_input+ output_tokens * self.cost_per_1m_output) / 1_000_000


REGISTRY: dict[str, ModelConfig] = {
    "ollama-local": ModelConfig(
        provider="ollama",
        model_id="llama3.2:3b",
        cost_per_1m_input=0.0,
        cost_per_1m_output=0.0,
        avg_latency_ms=6500,
        quality_tier=QualityTier.LOW,
    ),
    "gemini-lite": ModelConfig(
        provider="gemini",
        model_id="gemini-2.5-flash-lite",
        cost_per_1m_input=0.10,
        cost_per_1m_output=0.40,
        avg_latency_ms=400,
        quality_tier=QualityTier.LOW,
    ),
    "groq-20b": ModelConfig(
        provider="groq",
        model_id="openai/gpt-oss-20b",
        cost_per_1m_input=0.075,
        cost_per_1m_output=0.30,
        avg_latency_ms=600,
        quality_tier=QualityTier.MEDIUM,
    ),
    "groq-120b": ModelConfig(
        provider="groq",
        model_id="openai/gpt-oss-120b",
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        avg_latency_ms=600,
        quality_tier=QualityTier.MEDIUM,
    ),
    "gemini-pro": ModelConfig(
        provider="gemini",
        model_id="gemini-3.1-pro",
        cost_per_1m_input=2.00,
        cost_per_1m_output=12.00,
        avg_latency_ms=2000,
        quality_tier=QualityTier.HIGH,
    ),
}