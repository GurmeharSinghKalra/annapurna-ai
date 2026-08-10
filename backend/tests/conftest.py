"""Test bootstrap.

Environment is configured *before* the application package is imported, because
settings are read once per process. Setting the keys to empty strings (rather
than deleting them) also stops a developer's real `.env` from leaking live API
credentials into a test run: `load_dotenv` does not overwrite existing keys.
"""

import os
import shutil
import tempfile
from pathlib import Path

TMP_ROOT = Path(os.environ.get("ANNAPURNA_TEST_ROOT") or tempfile.mkdtemp(prefix="annapurna-tests-"))
os.environ["ANNAPURNA_TEST_ROOT"] = str(TMP_ROOT)

os.environ["ANNAPURNA_DB_PATH"] = str(TMP_ROOT / "test.sqlite")
os.environ["ANNAPURNA_MODEL_DIR"] = str(TMP_ROOT / "models")
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["LOGIN_ATTEMPT_LIMIT"] = "5"
os.environ["LOGIN_ATTEMPT_WINDOW_SECONDS"] = "300"
os.environ["GEMINI_API_KEY"] = ""
os.environ["OPENWEATHER_API_KEY"] = ""
os.environ["AGMARKNET_SOURCE_URL"] = ""
os.environ["ENAM_SOURCE_URL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import ml_model  # noqa: E402
from app.database import get_connection, init_database  # noqa: E402
from app.gemini_service import gemini_service  # noqa: E402
from app.main import app, login_limiter  # noqa: E402

from tests.helpers import VALID_FARM  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TMP_ROOT, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def schema():
    """Create the schema once, before any function-scoped fixture touches it.

    Tests that never build a TestClient still need the tables, because lifespan
    is what normally creates them.
    """
    init_database()


@pytest.fixture
def client():
    # The context manager runs lifespan, which creates the schema.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def isolate_state():
    """Each test starts with an empty database, no throttle history, no model."""
    with get_connection() as connection:
        for table in ("sessions", "recommendation_history", "users"):
            connection.execute(f"DELETE FROM {table}")
    login_limiter.reset()
    ml_model.reset_cache()
    yield


@pytest.fixture(autouse=True)
def disable_live_gemini():
    """Keep the suite deterministic and off live API quota."""
    gemini_service.client = None
    yield
    gemini_service.client = None


@pytest.fixture
def farm():
    return dict(VALID_FARM)


@pytest.fixture
def admin_headers():
    return {"X-Admin-Token": "test-admin-token"}


@pytest.fixture
def registered(client):
    """Register a farmer and return (headers, user, password)."""

    def _register(phone="9811100001", password="secret1234", name="Test Farmer"):
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "phone": phone,
                "password": password,
                "language": "English",
                "location": "Hisar, Haryana",
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        return (
            {"Authorization": f"Bearer {payload['access_token']}"},
            payload["user"],
            password,
        )

    return _register
