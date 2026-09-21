import asyncio

from app.config import get_settings
from app.models.registry import REGISTRY
from app.providers.groq import GroqProvider


async def main():
    settings = get_settings()
    provider = GroqProvider(api_key=settings.groq_api_key)
    config = REGISTRY["groq-20b"]

    response = await provider.send("Say hello in exactly five words.", config)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())