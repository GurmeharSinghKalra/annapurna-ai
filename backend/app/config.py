import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(REPO_ROOT / ".env")

DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)


def _optional(name: str) -> str | None:
    return os.getenv(name) or None


def _csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """Snapshot of process configuration.

    Build it through `get_settings()` so the environment is read once per process
    instead of at class-definition time, and so tests can reset it deliberately.
    """

    openweather_api_key: str | None
    gemini_api_key: str | None
    gemini_model: str
    agmarknet_source_url: str | None
    enam_source_url: str | None
    admin_token: str | None
    cors_origins: tuple[str, ...]
    database_path: Path
    model_dir: Path
    session_ttl_hours: int
    max_upload_bytes: int
    login_attempt_limit: int
    login_attempt_window_seconds: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openweather_api_key=_optional("OPENWEATHER_API_KEY"),
            gemini_api_key=_optional("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            agmarknet_source_url=_optional("AGMARKNET_SOURCE_URL"),
            enam_source_url=_optional("ENAM_SOURCE_URL"),
            admin_token=_optional("ADMIN_TOKEN"),
            cors_origins=_csv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
            database_path=Path(
                os.getenv("ANNAPURNA_DB_PATH", str(BACKEND_DIR / "data" / "annapurna_ai.sqlite"))
            ),
            model_dir=Path(os.getenv("ANNAPURNA_MODEL_DIR", str(BACKEND_DIR / "models"))),
            session_ttl_hours=_int("SESSION_TTL_HOURS", 24 * 14),
            max_upload_bytes=_int("MAX_UPLOAD_BYTES", 8 * 1024 * 1024),
            login_attempt_limit=_int("LOGIN_ATTEMPT_LIMIT", 10),
            login_attempt_window_seconds=_int("LOGIN_ATTEMPT_WINDOW_SECONDS", 300),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def reset_settings_cache() -> None:
    """Drop the cached settings so the next call re-reads the environment."""
    get_settings.cache_clear()
