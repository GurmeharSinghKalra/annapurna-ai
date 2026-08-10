import httpx

from .config import settings
from .schemas import FarmProfile

MARKET_NAMES = {
    "Rice": "Paddy (common)", "Maize": "Maize", "Cotton": "Cotton", "Wheat": "Wheat",
    "Mustard": "Mustard seed", "Chickpea": "Gram", "Sugarcane": "Sugarcane",
    "Pearl Millet": "Bajra",
}


def integration_status() -> dict:
    return {
        "soilgrids": "adapter_ready",
        "isro_bhuvan": "adapter_ready",
        "openweather": "configured" if settings.openweather_api_key else "missing_api_key",
        "agmarknet": "configured" if settings.agmarknet_source_url else "placeholder_dataset",
        "enam": "configured" if settings.enam_source_url else "placeholder_dataset",
        "gemini": "configured" if settings.gemini_api_key else "missing_api_key",
        "gemini_model": settings.gemini_model,
        "genai": "gemini" if settings.gemini_api_key else "local_advisory_fallback",
    }


async def fetch_weather(farm: FarmProfile) -> dict:
    if settings.openweather_api_key:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": farm.location,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "source": "OpenWeatherMap live",
                "location": farm.location,
                "temperature": payload.get("main", {}).get("temp", farm.temperature),
                "humidity": payload.get("main", {}).get("humidity", farm.humidity),
                "rainfall": payload.get("rain", {}).get("1h", farm.rainfall),
                "alert": payload.get("weather", [{}])[0].get("description", "Weather fetched"),
            }

    alert = "Weather is workable"
    if farm.rainfall < 40:
        alert = "Low rainfall alert"
    elif farm.rainfall > 180:
        alert = "Waterlogging risk"
    return {
        "source": "manual weather fallback",
        "location": farm.location,
        "temperature": farm.temperature,
        "humidity": farm.humidity,
        "rainfall": farm.rainfall,
        "alert": alert,
    }


def soil_profile(farm: FarmProfile) -> dict:
    nutrient_average = round((farm.nitrogen + farm.phosphorus + farm.potassium) / 3)
    ph_score = max(0, round(100 - abs(farm.ph - 6.8) * 22))
    health_score = round((nutrient_average * 0.55) + (ph_score * 0.45))
    actions = []
    if farm.ph < 5.8:
        actions.append("Discuss agricultural lime application with a local soil expert.")
    elif farm.ph > 7.8:
        actions.append("Add organic matter and use locally recommended amendments for alkaline soil.")
    if farm.nitrogen < 45:
        actions.append("Prioritize split nitrogen application or a legume rotation.")
    if farm.phosphorus < 40:
        actions.append("Confirm phosphorus requirement with a soil test before basal application.")
    if farm.potassium < 40:
        actions.append("Check potassium requirement, especially for water-stress resilience.")
    if not actions:
        actions.append("Maintain organic matter and repeat a laboratory soil test before the next major season.")
    return {
        "source": "farmer inputs with SoilGrids/ISRO-ready adapter",
        "location": farm.location,
        "soil_type": farm.soil_type,
        "ph": farm.ph,
        "nitrogen": farm.nitrogen,
        "phosphorus": farm.phosphorus,
        "potassium": farm.potassium,
        "health_score": health_score,
        "classification": "good" if health_score >= 70 else "attention needed" if health_score < 50 else "moderate",
        "actions": actions,
        "note": "Values remain farmer-entered until coordinates or an official soil-test feed are configured.",
    }


def market_profile(farm: FarmProfile, crop: str, expected_profit: int) -> dict:
    from .recommender import CROPS

    crop_data = next(item for item in CROPS if item["crop"] == crop)
    source = "curated demo market profile"
    if settings.agmarknet_source_url or settings.enam_source_url:
        source = "configured market data adapter"
    price_band = "medium-high" if expected_profit >= 70000 else "medium"
    return {
        "source": source,
        "crop": crop,
        "commodity": MARKET_NAMES.get(crop, crop),
        "expected_profit": expected_profit,
        "price_band": price_band,
        "modal_price_per_quintal": crop_data["market_price"],
        "trend_percent": crop_data["market_trend"],
        "trend": "rising" if crop_data["market_trend"] > 0 else "softening",
        "agmarknet": settings.agmarknet_source_url or "not configured",
        "enam": settings.enam_source_url or "not configured",
        "note": "Planning baseline; verify the current mandi price before sale or investment.",
    }
