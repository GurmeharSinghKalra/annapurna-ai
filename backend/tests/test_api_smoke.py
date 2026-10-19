from io import BytesIO
import asyncio

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app import gemini_service as gemini_module
from app.gemini_service import DiseaseAnalysis, RecommendationInsight, gemini_service
from app import integrations, ml_model
from app.recommender import recommend
from app.schemas import FarmProfile


client = TestClient(app)


def valid_leaf_image_bytes() -> bytes:
    image = Image.new("RGB", (8, 8), color=(70, 130, 50))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def disable_live_gemini(monkeypatch):
    """Keep the test suite deterministic and avoid consuming live API quota."""
    monkeypatch.setattr(gemini_service, "client", None)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_local_frontend_origin_is_allowed_by_cors():
    response = client.options(
        "/analysis",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert response.headers.get("access-control-allow-credentials") is None


def test_api_rejects_invalid_farm_and_oversized_chat_input():
    invalid_farm = client.post("/analysis", json={"season": "Monsoon", "soil_type": "Unknown"})
    assert invalid_farm.status_code == 422
    oversized_chat = client.post("/chat", json={"question": "a" * 1201, "farm": {}})
    assert oversized_chat.status_code == 422
    negative_expense = client.post("/finance/season-plan", json={"farm": {}, "actual_expenses": {"Labour": -1}})
    assert negative_expense.status_code == 422


def test_corrupt_optional_ml_artifact_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(ml_model.joblib, "load", lambda path: (_ for _ in ()).throw(ValueError("corrupt model")))
    ml_model._load_model.cache_clear()
    try:
        assert ml_model.model_available() is False
        assert ml_model.predict_crop(FarmProfile()) == (None, 0.0)
    finally:
        ml_model._load_model.cache_clear()


def test_gemini_timeout_uses_local_fallback(monkeypatch):
    class FakeModels:
        async def generate_content(self, **kwargs):
            await asyncio.sleep(1)

    class FakeClient:
        class aio:
            models = FakeModels()

    async def timeout(awaitable, timeout):
        awaitable.close()
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(gemini_service, "client", FakeClient())
    monkeypatch.setattr(gemini_module.asyncio, "wait_for", timeout)
    farm = FarmProfile()
    answer = asyncio.run(gemini_service.chat_answer("How should I irrigate?", "Maize", farm, recommend(farm)[0]))
    assert answer is None


def test_recommendations():
    farm = {
        "farmer_name": "Demo Farmer",
        "phone": "9999999999",
        "location": "Sonipat, Haryana",
        "language": "English",
        "land_size": 2,
        "season": "Kharif",
        "soil_type": "Alluvial",
        "ph": 6.6,
        "nitrogen": 62,
        "phosphorus": 41,
        "potassium": 48,
        "temperature": 29,
        "humidity": 64,
        "rainfall": 115,
        "budget": 35000,
        "market_priority": "Balanced",
    }

    response = client.post("/recommendations", json=farm)
    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert recommendations
    assert response.json()["ai_provider"] in {"gemini", "local_fallback"}
    assert "ai_explanation" in response.json()
    assert recommendations[0]["crop"] in {"Maize", "Sugarcane", "Cotton", "Rice"}
    for recommendation in recommendations:
        assert recommendation["estimated_revenue"] == recommendation["expected_yield"] * recommendation["market_price"]
        assert recommendation["expected_profit"] == recommendation["estimated_revenue"] - recommendation["estimated_cost"]

def test_chat():
    response = client.post(
        "/chat",
        json={
            "question": "How should I irrigate?",
            "crop": "Maize",
            "farm": {
                "season": "Kharif",
                "soil_type": "Alluvial",
                "land_size": 2,
                "ph": 6.6,
                "nitrogen": 62,
                "phosphorus": 41,
                "potassium": 48,
                "temperature": 29,
                "humidity": 64,
                "rainfall": 115,
                "budget": 35000,
            },
        },
    )
    assert response.status_code == 200
    assert "answer" in response.json()
    assert response.json()["provider"] in {"gemini", "local_fallback"}

    hindi_response = client.post(
        "/chat",
        json={
            "question": "Mujhe kya karna chahiye?",
            "crop": "Maize",
            "farm": {
                "language": "Hindi",
                "season": "Kharif",
                "soil_type": "Alluvial",
                "land_size": 2,
                "ph": 6.6,
                "nitrogen": 62,
                "phosphorus": 41,
                "potassium": 48,
                "temperature": 29,
                "humidity": 64,
                "rainfall": 115,
                "budget": 35000,
            },
        },
    )
    assert hindi_response.status_code == 200
    assert "\u0938\u0932\u093e\u0939" in hindi_response.json()["answer"]


def test_integrations_and_anonymous_api_boundary():
    status_response = client.get("/integrations/status")
    assert status_response.status_code == 200
    assert "openweather" in status_response.json()
    assert "gemini" in status_response.json()
    assert "gemini_model" in status_response.json()
    assert client.post("/auth/register").status_code == 404
    assert client.get("/history").status_code == 404


def test_disease_screening_fallback_or_gemini():
    response = client.post(
        "/disease",
        files={"file": ("leaf.png", valid_leaf_image_bytes(), "image/png")},
        data={"crop": "Maize"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] in {"gemini", "local_fallback"}
    assert "prediction" in payload
    assert "advisory" in payload


def test_disease_rejects_non_image_bytes_even_when_mime_type_claims_image():
    response = client.post(
        "/disease",
        files={"file": ("leaf.png", b"this is not image data", "image/png")},
    )
    assert response.status_code == 422


def test_disease_rejects_declared_oversized_upload_before_file_parsing():
    response = client.post(
        "/disease",
        content=b"small-body",
        headers={"content-type": "multipart/form-data; boundary=ignored", "content-length": str((8 * 1024 * 1024) + (128 * 1024) + 1)},
    )
    assert response.status_code == 413


def test_gemini_routes_return_structured_provider_metadata(monkeypatch):
    async def fake_insight(farm, recommendations):
        return RecommendationInsight(
            summary="Maize matches the supplied field conditions.",
            priority_action="Confirm drainage before sowing.",
            risk_note="Profit remains an estimate.",
        )

    async def fake_chat(question, crop, farm, recommendation, finance=None):
        return f"Gemini answer for {crop}: {question}; finance={finance.crop if finance else 'none'}"

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

    farm = {
        "location": "Sonipat, Haryana",
        "season": "Kharif",
        "soil_type": "Alluvial",
        "land_size": 2,
        "ph": 6.6,
        "nitrogen": 62,
        "phosphorus": 41,
        "potassium": 48,
        "temperature": 29,
        "humidity": 64,
        "rainfall": 115,
        "budget": 35000,
    }

    recommendation_response = client.post("/recommendations", json=farm)
    assert recommendation_response.json()["ai_provider"] == "gemini"
    assert recommendation_response.json()["ai_explanation"]["priority_action"]

    chat_response = client.post("/chat", json={"question": "How should I irrigate?", "crop": "Maize", "farm": farm})
    assert chat_response.json()["provider"] == "gemini"
    assert "How should I irrigate?" in chat_response.json()["answer"]

    finance_chat_response = client.post(
        "/chat",
        json={
            "question": "Can I cover my cultivation cost?",
            "crop": "Maize",
            "farm": farm,
            "finance": {
                "crop": "Maize",
                "planning_source": "curated planning baseline",
                "actual_cost": 52000,
                "expected_revenue": 108000,
                "expected_profit": 56000,
                "break_even_price_per_quintal": 1083,
                "working_capital_gap": 17000,
            },
        },
    )
    assert finance_chat_response.json()["provider"] == "gemini"
    assert "finance=Maize" in finance_chat_response.json()["answer"]

    disease_response = client.post(
        "/disease",
        files={"file": ("leaf.png", valid_leaf_image_bytes(), "image/png")},
        data={"crop": "Maize"},
    )
    assert disease_response.json()["provider"] == "gemini"
    assert disease_response.json()["urgency"] == "moderate"


def test_weather_soil_and_market():
    farm = {
        "location": "Sonipat, Haryana",
        "season": "Kharif",
        "soil_type": "Alluvial",
        "land_size": 2,
        "ph": 6.6,
        "nitrogen": 62,
        "phosphorus": 41,
        "potassium": 48,
        "temperature": 29,
        "humidity": 64,
        "rainfall": 115,
        "budget": 35000,
    }
    for route in ["/weather", "/soil", "/market"]:
        response = client.post(route, json=farm)
        assert response.status_code == 200
        assert "source" in response.json()


def test_weather_uses_labelled_manual_fallback_when_live_request_fails(monkeypatch):
    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            raise integrations.httpx.ConnectError("offline")

    class WeatherSettings:
        openweather_api_key = "test-key"

    monkeypatch.setattr(integrations, "settings", WeatherSettings())
    monkeypatch.setattr(integrations.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    response = client.post("/weather", json={"location": "Sonipat, Haryana", "rainfall": 30})
    assert response.json()["source"] == "manual weather fallback (live request unavailable)"
    assert response.json()["alert"] == "Low rainfall alert"


def test_market_uses_configured_compatible_feed_and_finance_uses_its_price(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"commodity": "Maize", "modal_price_per_quintal": "2450", "market": "Sonipat", "date": "2026-10-17"}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse()

    class MarketSettings:
        agmarknet_source_url = "https://market.example.test/feed"
        enam_source_url = None

    monkeypatch.setattr(integrations, "settings", MarketSettings())
    monkeypatch.setattr(integrations.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    farm = {"location": "Sonipat, Haryana", "season": "Kharif", "soil_type": "Alluvial", "land_size": 2, "ph": 6.6, "nitrogen": 62, "phosphorus": 41, "potassium": 48, "temperature": 29, "humidity": 64, "rainfall": 115, "budget": 35000}
    market_response = client.post("/market", json=farm)
    assert market_response.status_code == 200
    assert market_response.json()["source"] == "Agmarknet live feed"
    assert market_response.json()["modal_price_per_quintal"] == 2450
    finance_response = client.post("/finance/season-plan", json={"farm": farm, "crop": "Maize"})
    assert finance_response.status_code == 200
    assert finance_response.json()["summary"]["planning_market_price_per_quintal"] == 2450


def test_complete_farm_analysis_connects_proposal_workflow(monkeypatch):
    async def no_gemini(farm, recommendations):
        return None

    monkeypatch.setattr(gemini_service, "recommendation_insight", no_gemini)
    response = client.post(
        "/analysis",
        json={
            "location": "Sonipat, Haryana",
            "season": "Rabi",
            "previous_crop": "Rice",
            "soil_type": "Alluvial",
            "land_size": 2,
            "ph": 6.6,
            "nitrogen": 46,
            "phosphorus": 38,
            "potassium": 42,
            "temperature": 21,
            "humidity": 58,
            "rainfall": 62,
            "budget": 60000,
            "market_priority": "Sustainability",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendations"]
    assert payload["weather"]["source"]
    assert 0 <= payload["soil"]["health_score"] <= 100
    assert payload["soil"]["actions"]
    assert payload["markets"][0]["modal_price_per_quintal"] > 0
    top = payload["recommendations"][0]
    assert top["estimated_cost"] > 0
    assert top["estimated_revenue"] > top["estimated_cost"]
    assert 0 < top["profit_margin"] < 100
    assert 0 < top["sustainability_score"] <= 100


def test_season_financial_plan_has_expenses_cashflow_and_risk_scenarios():
    response = client.post(
        "/finance/season-plan",
        json={
            "farm": {
                "season": "Kharif",
                "soil_type": "Alluvial",
                "land_size": 2,
                "ph": 6.6,
                "nitrogen": 62,
                "phosphorus": 41,
                "potassium": 48,
                "temperature": 29,
                "humidity": 64,
                "rainfall": 115,
                "budget": 35000,
            },
            "crop": "Maize",
            "actual_expenses": {"Labour": 12000, "Seeds and planting": 10000},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["crop"] == "Maize"
    assert len(payload["expenses"]) == 7
    assert len(payload["cash_flow"]) == 4
    assert len(payload["scenarios"]) == 4
    assert payload["summary"]["break_even_price_per_quintal"] > 0
    assert payload["summary"]["expected_revenue"] == (
        payload["summary"]["expected_yield_quintal"] * payload["summary"]["planning_market_price_per_quintal"]
    )
    assert payload["scenarios"][-1]["revenue"] < payload["scenarios"][0]["revenue"]


def test_recommendation_and_finance_share_the_same_baseline_revenue_model():
    farm = {"season": "Kharif", "soil_type": "Alluvial", "land_size": 2, "ph": 6.6, "nitrogen": 62, "phosphorus": 41, "potassium": 48, "temperature": 29, "humidity": 64, "rainfall": 115, "budget": 35000}
    recommendation = next(item for item in client.post("/recommendations", json=farm).json()["recommendations"] if item["crop"] == "Maize")
    finance = client.post("/finance/season-plan", json={"farm": farm, "crop": "Maize"}).json()
    assert finance["summary"]["expected_revenue"] == recommendation["estimated_revenue"]
    assert finance["summary"]["expected_profit"] == recommendation["expected_profit"]


def test_finance_uses_a_farmer_verified_price_for_only_that_plan():
    response = client.post(
        "/finance/season-plan",
        json={"farm": {"season": "Kharif", "soil_type": "Alluvial", "land_size": 2}, "crop": "Maize", "market_price_per_quintal": 2600},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["planning_source"] == "farmer-entered local mandi price"
    assert payload["summary"]["planning_market_price_per_quintal"] == 2600
    assert payload["summary"]["expected_revenue"] == payload["summary"]["expected_yield_quintal"] * 2600


def test_finance_rejects_a_crop_outside_the_current_recommendation_plan():
    response = client.post("/finance/season-plan", json={"farm": {"season": "Kharif", "soil_type": "Alluvial", "land_size": 2}, "crop": "Not a crop"})
    assert response.status_code == 422


def test_catalog_and_admin_summary():
    crops_response = client.get("/crops")
    assert crops_response.status_code == 200
    assert len(crops_response.json()["crops"]) >= 6

    summary_response = client.get("/admin/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["crop_count"] >= 6
    assert "integrations" in summary


def test_report_endpoint():
    response = client.post(
        "/reports/recommendation",
        json={
            "farmer_name": "Demo Farmer",
            "location": "Sonipat, Haryana",
            "season": "Kharif",
            "soil_type": "Alluvial",
            "land_size": 2,
            "ph": 6.6,
            "nitrogen": 62,
            "phosphorus": 41,
            "potassium": 48,
            "temperature": 29,
            "humidity": 64,
            "rainfall": 115,
            "budget": 35000,
        },
    )
    assert response.status_code == 200
    assert "Annapurna AI Crop Recommendation Report" in response.text
    assert "Recommended crop:" in response.text
