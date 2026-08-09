import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str | None = os.getenv("OPENWEATHER_API_KEY") or None
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    agmarknet_source_url: str | None = os.getenv("AGMARKNET_SOURCE_URL") or None
    enam_source_url: str | None = os.getenv("ENAM_SOURCE_URL") or None


settings = Settings()
