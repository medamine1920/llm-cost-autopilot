import asyncio

from app.config import get_settings
from app.models.registry import REGISTRY
from app.providers.ollama import OllamaProvider


async def main():
    settings = get_settings()
    provider = OllamaProvider()
    config = REGISTRY["ollama-local"]

    response = await provider.send("Say hello in exactly five words.", config)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())