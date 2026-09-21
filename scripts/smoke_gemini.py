import asyncio

from app.config import get_settings
from app.models.registry import REGISTRY
from app.providers.gemini import GeminiProvider


async def main():
    settings = get_settings()
    provider = GeminiProvider(api_key=settings.gemini_api_key)
    config = REGISTRY["gemini-lite"]

    response = await provider.send("Say hello in exactly five words.", config)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())