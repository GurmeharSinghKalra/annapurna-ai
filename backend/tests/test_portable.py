"""The Windows portable launcher must actually reach its own API.

The shipped build was non-functional end to end: the client bundle calls `/api/...` while the
launcher mounted the API at the root, so every call received an HTML page with status 200.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

DISTRIBUTION = Path(__file__).resolve().parents[2] / "distribution"


@pytest.fixture(scope="module")
def portable(tmp_path_factory):
    sys.path.insert(0, str(DISTRIBUTION))
    import portable_server

    frontend = tmp_path_factory.mktemp("frontend")
    (frontend / "index.html").write_text("<!doctype html><title>Annapurna</title><div id=root></div>")
    (frontend / "assets").mkdir()
    (frontend / "assets" / "index.js").write_text("console.log('app')")
    portable_server.FRONTEND_DIR = frontend
    portable_server.app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="portable-assets")

    with TestClient(portable_server.app) as client:
        yield client


def test_the_api_is_reachable_under_the_api_prefix(portable):
    response = portable.get("/api/health")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["status"] == "ok"


def test_the_database_schema_exists(portable):
    """A mounted sub-app's lifespan does not run, so without delegating it every account query
    failed with "no such table"."""
    response = portable.post(
        "/api/auth/register",
        json={"name": "Portable", "phone": "9812345678", "password": "portablepass1"},
    )
    assert response.status_code == 201, response.text


def test_the_full_planning_workflow_works_offline(portable):
    farm = {
        "farmer_name": "Portable",
        "location": "Sonipat, Haryana",
        "season": "Kharif",
        "soil_type": "Alluvial",
        "irrigation": "Assured",
        "land_size": 2,
        "ph": 6.6,
        "nitrogen": 62,
        "phosphorus": 41,
        "potassium": 48,
        "temperature": 29,
        "humidity": 64,
        "rainfall": 600,
        "budget": 120000,
    }
    analysis = portable.post("/api/analysis", json=farm)
    assert analysis.status_code == 200
    assert analysis.json()["recommendations"]

    plan = portable.post("/api/finance/season-plan", json={"farm": farm})
    assert plan.status_code == 200
    assert plan.json()["summary"]["break_even_price_per_quintal"] > 0


def test_the_web_interface_is_served(portable):
    index = portable.get("/")
    assert index.status_code == 200
    assert "text/html" in index.headers["content-type"]


def test_client_side_routes_fall_back_to_the_shell(portable):
    for route in ("/planner", "/finance", "/records"):
        response = portable.get(route)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


def test_path_traversal_serves_the_shell_not_the_file(portable):
    response = portable.get("/../../etc/passwd")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "root:" not in response.text
