"""Route-level behaviour: contract, validation and the honesty of what is returned."""

from __future__ import annotations

import pytest


def test_health_describes_which_capabilities_exist(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    for key in ("version", "environment", "ml_model", "generative_ai", "live_weather", "live_market", "database"):
        assert key in body
    # The in-process limiter does not work across replicas; saying so is part of the contract.
    assert "single replica" in body["rate_limiter"]


def test_readyz_reflects_the_database(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_crops_returns_the_catalogue_with_its_provenance(client):
    body = client.get("/crops").json()
    assert len(body["crops"]) == 8
    provenance = body["provenance"]
    assert "Haryana" in provenance["region"]
    assert provenance["price_season"]
    assert provenance["last_reviewed"]
    for crop in body["crops"]:
        assert crop["sources"]
        assert crop["reference_price_basis"]
        assert set(crop["yield_quintal_per_acre"]) == {"low", "typical", "high"}


def test_recommendations_carry_verdicts_limiters_and_a_price_basis(client, farm):
    body = client.post("/recommendations", json=farm).json()
    assert body["ai_provider"] == "local_fallback"
    for item in body["recommendations"]:
        assert 0 <= item["suitability"] <= 100
        assert item["verdict"]
        assert item["price_basis"]
        assert "limiters" in item
        assert item["economics"]["expected_profit_inr"]


def test_analysis_joins_the_whole_workflow(client, farm):
    body = client.post("/analysis", json=farm).json()
    assert body["recommendations"]
    assert body["weather"]["live"] is False
    assert 0 <= body["soil"]["health_score"] <= 100
    assert body["soil"]["actions"]
    assert body["markets"]
    assert body["crop_data"]["region"]
    assert body["analyzed_at"]


def test_analysis_does_not_overwrite_the_farmers_seasonal_rainfall(client, farm):
    """With no weather provider, nothing should silently replace what the farmer entered."""
    body = client.post("/analysis", json={**farm, "rainfall": 777}).json()
    assert body["weather"]["temperature"] == farm["temperature"]
    assert "rainfall" not in body["weather"]


def test_soil_interprets_readings_into_bands_and_actions(client, farm):
    body = client.post("/soil", json={**farm, "ph": 9.2, "nitrogen": 10}).json()
    assert body["live"] is False
    assert body["ph_classification"] == "strongly alkaline"
    assert body["nutrients"]["nitrogen"]["band"] == "very low"
    assert any("alkaline" in action.lower() or "gypsum" in action.lower() for action in body["actions"])
    assert any("nitrogen" in action.lower() for action in body["actions"])


def test_soil_says_nothing_is_needed_when_readings_are_good(client, farm):
    body = client.post("/soil", json={**farm, "ph": 7.0, "nitrogen": 70, "phosphorus": 70, "potassium": 70}).json()
    assert body["classification"] == "good"
    assert len(body["actions"]) == 1


def test_text_report_states_ranges_sources_and_the_disclaimer(client, farm):
    response = client.post("/reports/recommendation", json=farm)
    assert response.status_code == 200
    text = response.text
    assert "ANNAPURNA AI - CROP RECOMMENDATION REPORT" in text
    assert "EXPECTED RANGE" in text
    assert "poor season" in text
    assert "REFERENCE DATA" in text
    assert "not lending, credit, or investment advice" in text.lower()
    assert "OTHER OPTIONS CONSIDERED" in text


def test_finance_route_rejects_an_unknown_expense_category(client, farm):
    response = client.post("/finance/season-plan", json={"farm": farm, "actual_expenses": {"Bribes": 1}})
    assert response.status_code == 422
    assert "Bribes" in response.json()["detail"]


def test_finance_route_rejects_a_negative_expense(client, farm):
    response = client.post("/finance/season-plan", json={"farm": farm, "actual_expenses": {"Labour": -1}})
    assert response.status_code == 422


def test_finance_and_recommendations_agree_on_the_same_crop(client, farm):
    recommendation = next(
        item for item in client.post("/recommendations", json=farm).json()["recommendations"] if item["crop"] == "Maize"
    )
    plan = client.post("/finance/season-plan", json={"farm": farm, "crop": "Maize"}).json()
    assert plan["summary"]["expected_revenue"] == recommendation["estimated_revenue"]
    assert plan["summary"]["expected_profit"] == recommendation["expected_profit"]


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"season": "Monsoon"}, 422),
        ({"soil_type": "Moon dust"}, 422),
        ({"irrigation": "Magic"}, 422),
        ({"ph": 99}, 422),
        ({"ph": -1}, 422),
        ({"land_size": 0}, 422),
        ({"land_size": 99999}, 422),
        ({"rainfall": -5}, 422),
        ({"rainfall": 99999}, 422),
        ({"humidity": 500}, 422),
        ({"temperature": 999}, 422),
        ({"budget": -1}, 422),
        ({"farmer_name": ""}, 422),
        ({"farmer_name": "   "}, 422),
        ({"location": "x"}, 422),
    ],
)
def test_invalid_profiles_are_refused_with_422(client, farm, payload, expected):
    assert client.post("/analysis", json={**farm, **payload}).status_code == expected


def test_chat_input_limits_are_enforced(client, farm):
    assert client.post("/chat", json={"question": "a" * 1201, "farm": farm}).status_code == 422
    assert client.post("/chat", json={"question": "a", "farm": farm}).status_code == 422
    assert client.post("/chat", json={"question": "How much water?", "farm": farm}).status_code == 200


def test_admin_summary_reports_the_catalogue_and_integrations(client):
    body = client.get("/admin/summary").json()
    assert body["crop_count"] == 8
    assert body["crop_data"]["region"]
    assert "weather" in body["integrations"]


def test_openapi_document_builds(client):
    """A broken response model would only show up here, not in a route test."""
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    for route in ("/health", "/analysis", "/finance/season-plan", "/auth/login", "/plans", "/reports/pdf"):
        assert route in paths, route
