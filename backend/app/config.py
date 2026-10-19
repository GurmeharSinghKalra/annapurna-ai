import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


def cors_origins() -> tuple[str, ...]:
    configured = tuple(origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip())
    return configured or DEFAULT_CORS_ORIGINS


@dataclass(frozen=True)
class Settings:
    openweather_api_key: str | None = os.getenv("OPENWEATHER_API_KEY") or None
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    agmarknet_api_key: str | None = os.getenv("AGMARKNET_API_KEY") or None
    agmarknet_source_url: str | None = os.getenv("AGMARKNET_SOURCE_URL") or None
    enam_source_url: str | None = os.getenv("ENAM_SOURCE_URL") or None
    cors_origins: tuple[str, ...] = cors_origins()
    gemini_timeout_seconds: float = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))


settings = Settings()
