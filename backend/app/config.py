"""Runtime configuration.

Every value is read when ``Settings`` is built rather than at class-definition time, so tests and
the portable launcher can change the environment and call ``reload_settings()`` to pick it up.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent

# A backend-local .env wins over the repository-root one, so a developer can keep personal keys
# out of the shared file without editing it.
for candidate in (PROJECT_DIR / ".env", BACKEND_DIR / ".env"):
    if candidate.is_file():
        load_dotenv(candidate, override=True)

DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:5174",
    "http://localhost:5174",
)

# Only used when APP_ENV is not "production"; production refuses to start without a real secret.
_DEVELOPMENT_JWT_SECRET = "annapurna-development-only-secret-do-not-use-in-production"


class ConfigurationError(RuntimeError):
    """Raised when a production deployment is missing a setting it cannot safely default."""


def _text(name: str, default: str = "") -> str:
    return (os.getenv(name) or "").strip() or default


def _optional(name: str) -> str | None:
    return _text(name) or None


def _number(name: str, default: float) -> float:
    raw = _text(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("%s=%r is not a number; using %s", name, raw, default)
        return default


def _whole(name: str, default: int, minimum: int = 0) -> int:
    value = int(_number(name, default))
    return max(minimum, value)


def _flag(name: str, default: bool = False) -> bool:
    raw = _text(name).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def cors_origins() -> tuple[str, ...]:
    configured = tuple(origin.strip() for origin in _text("CORS_ORIGINS").split(",") if origin.strip())
    return configured or DEFAULT_CORS_ORIGINS


def _default_database_url() -> str:
    return f"sqlite+aiosqlite:///{(BACKEND_DIR / 'data' / 'annapurna.db').as_posix()}"


def _jwt_secret(app_env: str) -> str:
    secret = _text("JWT_SECRET")
    if secret:
        if len(secret) < 32:
            raise ConfigurationError("JWT_SECRET must be at least 32 characters")
        return secret
    if app_env == "production":
        raise ConfigurationError(
            "JWT_SECRET is required when APP_ENV=production. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    logger.warning(
        "JWT_SECRET is not set; using the shared development secret. "
        "Set JWT_SECRET before deploying anywhere reachable."
    )
    return _DEVELOPMENT_JWT_SECRET


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: _text("APP_ENV", "development").lower())

    # --- external providers -------------------------------------------------
    openweather_api_key: str | None = field(default_factory=lambda: _optional("OPENWEATHER_API_KEY"))
    gemini_api_key: str | None = field(default_factory=lambda: _optional("GEMINI_API_KEY"))
    gemini_model: str = field(default_factory=lambda: _text("GEMINI_MODEL", "gemini-3.8-flash"))
    gemini_timeout_seconds: float = field(default_factory=lambda: _number("GEMINI_TIMEOUT_SECONDS", 20))
    agmarknet_api_key: str | None = field(default_factory=lambda: _optional("AGMARKNET_API_KEY"))

    # --- http -----------------------------------------------------------------
    cors_origins: tuple[str, ...] = field(default_factory=cors_origins)
    weather_timeout_seconds: float = field(default_factory=lambda: _number("WEATHER_TIMEOUT_SECONDS", 8))
    market_timeout_seconds: float = field(default_factory=lambda: _number("MARKET_TIMEOUT_SECONDS", 12))

    # --- caching ----------------------------------------------------------------
    weather_cache_ttl_seconds: float = field(default_factory=lambda: _number("WEATHER_CACHE_TTL_SECONDS", 900))
    geocode_cache_ttl_seconds: float = field(default_factory=lambda: _number("GEOCODE_CACHE_TTL_SECONDS", 86_400))
    market_cache_ttl_minutes: float = field(default_factory=lambda: _number("MARKET_CACHE_TTL_MINUTES", 180))
    market_trend_window_days: int = field(default_factory=lambda: _whole("MARKET_TREND_WINDOW_DAYS", 14, 2))
    market_trend_min_points: int = field(default_factory=lambda: _whole("MARKET_TREND_MIN_POINTS", 3, 2))
    # A keyless community mirror of the government mandi dataset, so the product shows real
    # prices before anyone registers for a key. Narrower coverage and a shared rate limit, so a
    # configured AGMARKNET_API_KEY always takes precedence. Set false to use only official feeds.
    keyless_market_fallback: bool = field(default_factory=lambda: _flag("KEYLESS_MARKET_FALLBACK", True))
    # How long a "no price for this crop here" result is remembered, so an uncovered crop does not
    # spend a fresh upstream request on every analysis.
    market_miss_ttl_seconds: float = field(default_factory=lambda: _number("MARKET_MISS_TTL_SECONDS", 1_800))

    # --- database ---------------------------------------------------------------
    database_url: str = field(default_factory=lambda: _text("DATABASE_URL") or _default_database_url())
    db_pool_size: int = field(default_factory=lambda: _whole("DB_POOL_SIZE", 5, 1))
    db_max_overflow: int = field(default_factory=lambda: _whole("DB_MAX_OVERFLOW", 10, 0))
    db_pool_timeout: int = field(default_factory=lambda: _whole("DB_POOL_TIMEOUT", 30, 1))
    db_pool_recycle: int = field(default_factory=lambda: _whole("DB_POOL_RECYCLE", 1_800, 60))
    sql_echo: bool = field(default_factory=lambda: _flag("SQL_ECHO"))
    auto_create_tables: bool = field(
        default_factory=lambda: _flag("AUTO_CREATE_TABLES", _text("APP_ENV", "development").lower() != "production")
    )

    # --- auth ----------------------------------------------------------------------
    jwt_secret: str = field(default_factory=lambda: _jwt_secret(_text("APP_ENV", "development").lower()))
    jwt_issuer: str = field(default_factory=lambda: _text("JWT_ISSUER", "annapurna-ai"))
    access_token_ttl_minutes: int = field(default_factory=lambda: _whole("ACCESS_TOKEN_TTL_MINUTES", 30, 1))
    refresh_token_ttl_days: int = field(default_factory=lambda: _whole("REFRESH_TOKEN_TTL_DAYS", 30, 1))

    # --- abuse control -----------------------------------------------------------------
    ai_rate_limit_per_hour: int = field(default_factory=lambda: _whole("AI_RATE_LIMIT_PER_HOUR", 60, 0))
    analysis_rate_limit_per_hour: int = field(default_factory=lambda: _whole("ANALYSIS_RATE_LIMIT_PER_HOUR", 240, 0))

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


settings = Settings()


def reload_settings() -> Settings:
    """Rebuild settings from the current environment. Used by tests and the portable launcher."""
    global settings
    settings = Settings()
    return settings
