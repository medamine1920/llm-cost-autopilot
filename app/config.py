"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API."""

    app_name: str = "llm-cost-autopilot"
    version:str = "0.2.0"
    app_env: str = "development"
    log_level: str = "INFO"
    
    # Provider Credentials Keys
    groq_api_key: str = "Groq API Key"
    gemini_api_key: str = "Gemini API Key"
    ollama_base_url: str = "http://localhost:11434"
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()
