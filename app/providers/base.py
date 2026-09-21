"""Provider abstraction: one interface for every LLM backend."""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.models.registry import ModelConfig


class Response(BaseModel):
    """Standardized result from any provider."""

    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    model_id: str
    provider: str


class Provider(ABC):
    """Base class every provider implements."""

    @abstractmethod
    async def send(self, prompt: str, config: ModelConfig) -> Response:
        """Send a prompt, return a normalized Response."""
        print("send method not implemented for provider")
        
        