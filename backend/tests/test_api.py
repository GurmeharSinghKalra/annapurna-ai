"""Endpoint behaviour: validation, ownership, uploads, fallbacks, and reports."""

import httpx
import pytest

from app import integrations
from app.config import get_settings, reset_settings_cache
from app.gemini_service import DiseaseAnalysis, RecommendationInsight, gemini_service

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128


def test_health(client):
    payload = client.get("/health").json()
    assert payload["status"] == "ok"
    assert payload["service"] == "annapurna-ai"


def test_crop_catalog_exposes_the_economics_inputs(client):
    crops = client.get("/crops").json()["crops"]
    assert len(crops) == 8
    for crop in crops:
        assert crop["cost_per_acre"] > 0
        assert crop["yield_per_acre"] > 0
        assert crop["market_price"] > 0


def test_integration_status_lists_every_adapter(client):
    payload = client.get("/integrations/status").json()
    for key in ("soilgrids", "isro_bhuvan", "openweather", "agmarknet", "enam", "gemini"):
        assert key in payload


# ----- input validation ---------------------------------------------------- #


def test_an_empty_farm_profile_is_rejected(client):
    """A request describing no farm must not produce a confident recommendation."""
    assert client.post("/recommendations", json={}).status_code == 422


@pytest.mark.parametrize(
    "override",
    [
        {"season": "Monsoon"},
        {"soil_type": "Volcanic"},
        {"market_priority": "Whatever"},
        {"previous_crop": "Bananas"},
        {"ph": 15},
        {"ph": -1},
        {"land_size": 0},
        {"land_size": 1e12},
        {"humidity": 101},
        {"temperature": 500},
        {"rainfall": -5},
        {"budget": -1},
        {"phone": "12345"},
        {"location": ""},
        {"unexpected_field": 1},
    ],
)
def test_out_of_contract_inputs_are_rejected(client, farm, override):
    assert client.post("/recommendations", json={**farm, **override}).status_code == 422


def test_a_valid_profile_is_accepted(client, farm):
    payload = client.post("/recommendations", json=farm).json()
    assert payload["recommendations"]
    assert payload["ai_provider"] == "local_fallback"


# ----- history ownership --------------------------------------------------- #


def test_history_requires_authentication(client):
    assert client.get("/history").status_code == 401
    assert (
        client.post(
            "/history",
            json={
                "farmer_name": "X",
                "location": "Y",
                "crop": "Maize",
                "suitability": 50,
                "expected_profit": 1000,
            },
        ).status_code
        == 401
    )


def test_history_is_scoped_to_its_owner(client, registered):
    alice_headers, alice, _ = registered(phone="9811100001", name="Alice")
    bob_headers, _, _ = registered(phone="9811100002", name="Bob")

    record = {
        "farmer_name": alice["name"],
        "location": "Hisar",
        "crop": "Maize",
        "suitability": 80,
        "expected_profit": 50000,
    }
    assert client.post("/history", json=record, headers=alice_headers).status_code == 201

    assert len(client.get("/history", headers=alice_headers).json()["history"]) == 1
    assert client.get("/history", headers=bob_headers).json()["history"] == []


def test_history_rejects_an_unknown_crop(client, registered):
    headers, _, _ = registered()
    response = client.post(
        "/history",
        json={
            "farmer_name": "A",
            "location": "B",
            "crop": "Dragonfruit",
            "suitability": 50,
            "expected_profit": 1,
        },
        headers=headers,
    )
    assert response.status_code == 422


# ----- admin --------------------------------------------------------------- #


def test_admin_summary_requires_the_admin_token(client, admin_headers):
    assert client.get("/admin/summary").status_code == 403
    assert client.get("/admin/summary", headers={"X-Admin-Token": "wrong"}).status_code == 403
    assert client.get("/admin/summary", headers=admin_headers).status_code == 200


def test_admin_summary_is_disabled_when_no_token_is_configured(client, monkeypatch, admin_headers):
    monkeypatch.setenv("ADMIN_TOKEN", "")
    reset_settings_cache()
    try:
        assert client.get("/admin/summary", headers=admin_headers).status_code == 503
    finally:
        reset_settings_cache()


def test_admin_summary_counts_without_loading_rows(client, registered, admin_headers):
    headers, user, _ = registered()
    client.post(
        "/history",
        json={
            "farmer_name": user["name"],
            "location": "Hisar",
            "crop": "Maize",
            "suitability": 80,
            "expected_profit": 5000,
        },
        headers=headers,
    )
    payload = client.get("/admin/summary", headers=admin_headers).json()
    assert payload["history_count"] == 1
    assert payload["user_count"] == 1
    assert payload["crop_count"] == 8
    assert "state" in payload["ml_model"]


# ----- weather ------------------------------------------------------------- #


def test_weather_falls_back_and_labels_the_source(client, farm):
    payload = client.post("/weather", json=farm).json()
    assert payload["source"] == "manual weather fallback"
    assert payload["live"] is False
    assert payload["seasonal_rainfall_mm"] == farm["rainfall"]


class _FailingAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        raise httpx.ConnectError("upstream is down")


@pytest.fixture
def openweather_configured(monkeypatch):
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key-abc123")
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_an_upstream_weather_failure_degrades_instead_of_500(
    client, farm, monkeypatch, openweather_configured
):
    monkeypatch.setattr(integrations.httpx, "AsyncClient", _FailingAsyncClient)

    response = client.post("/weather", json=farm)
    assert response.status_code == 200
    assert response.json()["live"] is False
    assert "network error" in response.json()["note"]

    # The same failure must not take down the composite endpoint either.
    assert client.post("/analysis", json=farm).status_code == 200


def test_an_upstream_weather_error_does_not_leak_the_api_key(
    client, farm, monkeypatch, caplog, openweather_configured
):
    request = httpx.Request("GET", "https://api.openweathermap.org/data/2.5/weather?appid=test-key-abc123")
    response = httpx.Response(401, request=request)

    class _Unauthorized(_FailingAsyncClient):
        async def get(self, *args, **kwargs):
            raise httpx.HTTPStatusError("401", request=request, response=response)

    monkeypatch.setattr(integrations.httpx, "AsyncClient", _Unauthorized)

    with caplog.at_level("WARNING"):
        assert client.post("/weather", json=farm).status_code == 200

    assert "test-key-abc123" not in caplog.text


def test_live_weather_keeps_hourly_and_seasonal_rainfall_separate(
    client, farm, monkeypatch, openweather_configured
):
    class _Live(_FailingAsyncClient):
        async def get(self, *args, **kwargs):
            return httpx.Response(
                200,
                json={
                    "main": {"temp": 31.5, "humidity": 70},
                    "rain": {"1h": 3.2},
                    "weather": [{"description": "light rain"}],
                },
                request=httpx.Request("GET", "https://example.test"),
            )

    monkeypatch.setattr(integrations.httpx, "AsyncClient", _Live)

    payload = client.post("/weather", json=farm).json()
    assert payload["live"] is True
    assert payload["temperature"] == 31.5
    assert payload["recent_rainfall_mm"] == 3.2
    # 3.2 mm in an hour must never be mistaken for the seasonal total.
    assert payload["seasonal_rainfall_mm"] == farm["rainfall"]


# ----- disease uploads ----------------------------------------------------- #


def test_a_non_image_upload_is_rejected_despite_its_declared_type(client):
    response = client.post(
        "/disease", files={"file": ("payload.exe", b"MZ\x90\x00 definitely not an image", "image/png")}
    )
    assert response.status_code == 415


def test_an_empty_upload_is_rejected(client):
    assert client.post("/disease", files={"file": ("x.png", b"", "image/png")}).status_code == 400


def test_an_oversized_upload_is_rejected(client):
    limit = get_settings().max_upload_bytes
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * (limit + 1024)
    assert client.post("/disease", files={"file": ("big.png", payload, "image/png")}).status_code == 413


def test_a_real_image_is_accepted_and_reports_its_detected_type(client):
    payload = client.post("/disease", files={"file": ("leaf.png", PNG, "application/octet-stream")}).json()
    assert payload["image_type"] == "image/png"
    assert payload["provider"] == "local_fallback"


def test_the_disease_fallback_does_not_invent_a_diagnosis(client):
    """Without a model, the old code returned a fake 72%-confidence prediction."""
    payload = client.post("/disease", files={"file": ("leaf.png", PNG, "image/png")}).json()
    assert payload["confidence"] == 0.0
    assert payload["urgency"] == "unknown"
    assert "not analysed" in payload["advisory"]


# ----- chat ---------------------------------------------------------------- #


def test_chat_falls_back_locally(client, farm):
    payload = client.post(
        "/chat", json={"question": "How should I irrigate?", "crop": "Maize", "farm": farm}
    ).json()
    assert payload["provider"] == "local_fallback"
    assert payload["answer"]


def test_chat_answers_in_the_requested_language(client, farm):
    payload = client.post(
        "/chat",
        json={"question": "Mujhe kya karna chahiye?", "farm": {**farm, "language": "Hindi"}},
    ).json()
    assert "सलाह" in payload["answer"]


def test_chat_requires_a_question(client, farm):
    assert client.post("/chat", json={"question": "", "farm": farm}).status_code == 422


# ----- gemini-backed responses --------------------------------------------- #


def test_gemini_routes_report_structured_provider_metadata(client, farm, monkeypatch):
    async def fake_insight(farm_, recommendations):
        return RecommendationInsight(
            summary="Maize matches the supplied field conditions.",
            priority_action="Confirm drainage before sowing.",
            risk_note="Profit remains an estimate.",
        )

    async def fake_chat(question, crop, farm_, recommendation):
        return f"Gemini answer for {crop}: {question}"

    async def fake_disease(image_bytes, mime_type, crop=None):
        return DiseaseAnalysis(
            prediction="possible leaf spot",
            confidence=0.81,
            observations=["small visible lesions"],
            advisory="Isolate affected leaves and confirm with a local expert.",
            urgency="moderate",
        )

    monkeypatch.setattr(gemini_service, "recommendation_insight", fake_insight)
    monkeypatch.setattr(gemini_service, "chat_answer", fake_chat)
    monkeypatch.setattr(gemini_service, "disease_analysis", fake_disease)

    recommendation = client.post("/recommendations", json=farm).json()
    assert recommendation["ai_provider"] == "gemini"
    assert recommendation["ai_explanation"]["priority_action"]

    chat = client.post("/chat", json={"question": "How should I irrigate?", "crop": "Maize", "farm": farm}).json()
    assert chat["provider"] == "gemini"
    assert "How should I irrigate?" in chat["answer"]

    disease = client.post("/disease", files={"file": ("leaf.png", PNG, "image/png")}).json()
    assert disease["provider"] == "gemini"
    assert disease["urgency"] == "moderate"


# ----- composite analysis -------------------------------------------------- #


def test_analysis_reports_which_inputs_it_used(client, farm):
    payload = client.post("/analysis", json={**farm, "season": "Rabi", "previous_crop": "Rice"}).json()

    assert payload["recommendations"]
    assert payload["weather"]["source"]
    assert 0 <= payload["soil"]["health_score"] <= 100
    assert payload["soil"]["actions"]
    assert payload["markets"][0]["modal_price_per_quintal"] > 0

    used = payload["inputs_used"]
    assert used["rainfall_source"] == "farmer"
    assert used["temperature_source"] == "farmer"
    assert used["rainfall"] == farm["rainfall"]


def test_market_endpoint_labels_its_source(client, farm):
    payload = client.post("/market", json=farm).json()
    assert payload["live"] is False
    assert payload["source"] == "curated demo market profile"


# ----- reports ------------------------------------------------------------- #


def test_report_is_a_downloadable_text_file(client, farm):
    response = client.post("/reports/recommendation", json=farm)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "attachment" in response.headers["content-disposition"]
    assert "Annapurna AI Crop Recommendation Report" in response.text


def test_report_omits_identity_when_none_was_supplied(client, farm):
    """The old defaults stamped a placeholder name and phone onto every report."""
    text = client.post("/reports/recommendation", json=farm).text
    assert "Farmer:" not in text
    assert "9999999999" not in text


def test_report_includes_identity_when_supplied(client, farm):
    text = client.post(
        "/reports/recommendation", json={**farm, "farmer_name": "Real Farmer", "phone": "9811100001"}
    ).text
    assert "Farmer: Real Farmer" in text
    assert "Phone: 9811100001" in text


def test_report_economics_reconcile(client, farm):
    text = client.post("/reports/recommendation", json=farm).text
    recommendation = client.post("/recommendations", json=farm).json()["recommendations"][0]
    assert f"INR {recommendation['estimated_revenue']:,}" in text
    assert f"INR {recommendation['expected_profit']:,}" in text
