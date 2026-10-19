"""Database engine, session factory, and URL normalisation.

The product supports two deployments from one setting:

* ``sqlite+aiosqlite`` for local development and the portable Windows build, and
* ``postgresql+asyncpg`` for hosted deployments (Neon, RDS, Cloud SQL, ...).

Managed Postgres providers hand out libpq-style URLs (``postgresql://...?sslmode=require``).
``asyncpg`` does not understand ``sslmode`` or the ``postgres://`` scheme, so the URL is
normalised here instead of asking every operator to rewrite it by hand.
"""

from __future__ import annotations

import ssl
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

# libpq SSL modes that asyncpg cannot be given in the URL. Mapped to a connect argument.
_SSL_REQUIRED_MODES = {"require", "verify-ca", "verify-full"}
_SSL_DISABLED_MODES = {"disable", "allow", "prefer"}


class Base(DeclarativeBase):
    """Declarative base for every Annapurna table."""


def normalise_database_url(url: str) -> tuple[str, dict]:
    """Return an async-driver URL plus the connect args its driver needs.

    Accepts the copy-paste URL that managed Postgres providers display and converts it to the
    asyncpg dialect, lifting ``sslmode`` and ``channel_binding`` out of the query string.
    """
    if url.startswith("sqlite+aiosqlite://"):
        return url, {}
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1), {}

    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in {"postgres", "postgresql", "postgresql+psycopg2", "postgresql+psycopg"}:
        scheme = "postgresql+asyncpg"
    elif scheme != "postgresql+asyncpg":
        # An explicitly chosen non-Postgres async driver is passed through untouched.
        return url, {}

    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)]
    connect_args: dict = {}
    remaining: list[tuple[str, str]] = []
    for key, value in query:
        lowered = key.lower()
        if lowered == "sslmode":
            mode = value.lower()
            if mode in _SSL_REQUIRED_MODES:
                context = ssl.create_default_context()
                if mode == "require":
                    # libpq's `require` encrypts without verifying; asyncpg verifies by default.
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                connect_args["ssl"] = context
            elif mode in _SSL_DISABLED_MODES:
                connect_args["ssl"] = False
        elif lowered in {"channel_binding", "options", "target_session_attrs", "application_name"}:
            # Recognised libpq parameters that asyncpg either infers or does not accept in the URL.
            continue
        else:
            remaining.append((key, value))

    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(remaining), parts.fragment)), connect_args


def _engine_kwargs(url: str, connect_args: dict) -> dict:
    kwargs: dict = {"echo": settings.sql_echo, "future": True, "connect_args": connect_args}
    if url.startswith("sqlite"):
        # SQLite has no server-side pool to size, and the file must exist before first connect.
        database_path = url.split("///", 1)[-1]
        if database_path and database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        return kwargs
    kwargs.update(
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        # Serverless Postgres closes idle connections; recycle before the server does it for us.
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
    )
    return kwargs


DATABASE_URL, CONNECT_ARGS = normalise_database_url(settings.database_url)

engine: AsyncEngine = create_async_engine(DATABASE_URL, **_engine_kwargs(DATABASE_URL, CONNECT_ARGS))

SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one transaction-scoped session per request."""
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def ping() -> bool:
    """Return True when the configured database answers a trivial query."""
    from sqlalchemy import text

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def dispose() -> None:
    await engine.dispose()
