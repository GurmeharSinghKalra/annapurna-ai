import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.gemini_service import DiseaseAnalysis, RecommendationInsight, gemini_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_live_gemini(monkeypatch):
    """Keep the test suite deterministic and avoid consuming live API quota."""
    monkeypatch.setattr(gemini_service, "client", None)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_recommendations_and_history():
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

    record = {
        "farmer_name": "Demo Farmer",
        "location": "Sonipat, Haryana",
        "crop": recommendations[0]["crop"],
        "suitability": recommendations[0]["suitability"],
        "expected_profit": recommendations[0]["expected_profit"],
    }
    save_response = client.post("/history", json=record)
    assert save_response.status_code == 200
    assert save_response.json()["saved"] is True

    history_response = client.get("/history")
    assert history_response.status_code == 200
    assert history_response.json()["history"][0]["crop"] == recommendations[0]["crop"]


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


def test_auth_and_integrations():
    phone = "9888800001"
    response = client.post(
        "/auth/register",
        json={
            "name": "Test Farmer",
            "phone": phone,
            "password": "secret123",
            "language": "Hindi",
            "location": "Hisar, Haryana",
        },
    )
    assert response.status_code in {200, 409}

    login_response = client.post(
        "/auth/login",
        json={"phone": phone, "password": "secret123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["phone"] == phone

    status_response = client.get("/integrations/status")
    assert status_response.status_code == 200
    assert "openweather" in status_response.json()
    assert "gemini" in status_response.json()
    assert "gemini_model" in status_response.json()


def test_disease_screening_fallback_or_gemini():
    response = client.post(
        "/disease",
        files={"file": ("leaf.png", b"not-a-real-image-but-valid-upload-bytes", "image/png")},
        data={"crop": "Maize"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] in {"gemini", "local_fallback"}
    assert "prediction" in payload
    assert "advisory" in payload


def test_gemini_routes_return_structured_provider_metadata(monkeypatch):
    async def fake_insight(farm, recommendations):
        return RecommendationInsight(
            summary="Maize matches the supplied field conditions.",
            priority_action="Confirm drainage before sowing.",
            risk_note="Profit remains an estimate.",
        )

    async def fake_chat(question, crop, farm, recommendation):
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

    disease_response = client.post(
        "/disease",
        files={"file": ("leaf.png", b"image-bytes", "image/png")},
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
