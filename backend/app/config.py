import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str | None = os.getenv("OPENWEATHER_API_KEY") or None
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY") or None
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    agmarknet_source_url: str | None = os.getenv("AGMARKNET_SOURCE_URL") or None
    enam_source_url: str | None = os.getenv("ENAM_SOURCE_URL") or None


settings = Settings()
