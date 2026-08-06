from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
