"""Test configuration.

Two properties the previous suite lacked:

* **Hermetic.** Four of its tests failed the moment ``AGMARKNET_API_KEY`` was set, and it made
  real DNS and HTTPS calls to api.data.gov.in, so it was green only on a machine with no
  credentials — exactly the configuration nobody deploys. Here the environment is pinned before
  the app is imported and outbound HTTP is blocked at the transport, so a stray real request
  fails loudly instead of silently passing or hanging CI.
* **Isolated.** Each test gets an empty database, so ordering cannot make a test pass.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Must be set before `app.config` is imported, since settings are read at construction.
_TMP = Path(tempfile.mkdtemp(prefix="annapurna-tests-"))
os.environ.update(
    APP_ENV="test",
    DATABASE_URL=f"sqlite+aiosqlite:///{(_TMP / 'test.db').as_posix()}",
    JWT_SECRET="test-secret-key-that-is-long-enough-for-validation",
    AUTO_CREATE_TABLES="true",
    OPENWEATHER_API_KEY="",
    GEMINI_API_KEY="",
    AGMARKNET_API_KEY="",
    KEYLESS_MARKET_FALLBACK="false",
    CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173",
    AI_RATE_LIMIT_PER_HOUR="1000",
    ANALYSIS_RATE_LIMIT_PER_HOUR="5000",
)

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db as database  # noqa: E402
from app import models  # noqa: F401,E402  - registers the tables
from app.db import Base  # noqa: E402
from app.deps import limiter  # noqa: E402
from app.gemini_service import gemini_service  # noqa: E402
from app.main import app  # noqa: E402


class BlockedNetwork(RuntimeError):
    """Raised when a test would make a real outbound request."""


@pytest.fixture(autouse=True)
def no_outbound_http(monkeypatch, request):
    """Fail any unmocked outbound HTTP. Tests that need a feed install their own transport."""
    if "allow_http" in request.keywords:
        return

    async def refuse(self, *args, **kwargs):
        raise BlockedNetwork("A test attempted a real outbound HTTP request. Mock the transport instead.")

    monkeypatch.setattr(httpx.AsyncClient, "send", refuse, raising=False)
    monkeypatch.setattr(httpx.AsyncClient, "get", refuse, raising=False)


@pytest.fixture(autouse=True)
def no_live_gemini(monkeypatch):
    """Keep every test deterministic and off the billing meter."""
    monkeypatch.setattr(gemini_service, "client", None)


@pytest.fixture(autouse=True)
def reset_market_misses():
    """The negative-lookup cache is process-global; one test's miss must not shadow another."""
    from app.market_data import clear_miss_cache

    clear_miss_cache()
    yield
    clear_miss_cache()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """The limiter is process-global; without this, one test's requests throttle another's."""
    limiter._hits.clear()
    yield
    limiter._hits.clear()


@pytest.fixture(autouse=True)
async def clean_database():
    """Drop and recreate every table around each test, so order cannot affect the result."""
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def farm() -> dict:
    """A realistic, complete Haryana kharif profile."""
    return {
        "farmer_name": "Demo Farmer",
        "location": "Sonipat, Haryana",
        "language": "English",
        "land_size": 2,
        "season": "Kharif",
        "previous_crop": "Wheat",
        "soil_type": "Alluvial",
        "irrigation": "Assured",
        "ph": 6.6,
        "nitrogen": 62,
        "phosphorus": 41,
        "potassium": 48,
        "temperature": 29,
        "humidity": 64,
        "rainfall": 600,
        "budget": 120000,
        "market_priority": "Balanced",
    }


@pytest.fixture
def account(client):
    """A registered farmer plus the Authorization header for them."""
    payload = {"name": "Gurmehar", "phone": "9876543210", "password": "strongpass123", "location": "Sonipat, Haryana"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "farmer": body["farmer"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "refresh_token": body["refresh_token"],
        "password": payload["password"],
        "phone": payload["phone"],
    }
