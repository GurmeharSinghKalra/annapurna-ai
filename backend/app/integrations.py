import httpx

from .config import settings
from .schemas import FarmProfile


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
    return {
        "source": "SoilGrids/ISRO Bhuvan adapter placeholder",
        "location": farm.location,
        "soil_type": farm.soil_type,
        "ph": farm.ph,
        "nitrogen": farm.nitrogen,
        "phosphorus": farm.phosphorus,
        "potassium": farm.potassium,
        "note": "Connect SoilGrids or ISRO Bhuvan lookup for live regional soil data.",
    }


def market_profile(farm: FarmProfile, crop: str, expected_profit: int) -> dict:
    source = "curated demo market profile"
    if settings.agmarknet_source_url or settings.enam_source_url:
        source = "configured market data adapter"
    price_band = "medium-high" if expected_profit >= 70000 else "medium"
    return {
        "source": source,
        "crop": crop,
        "expected_profit": expected_profit,
        "price_band": price_band,
        "agmarknet": settings.agmarknet_source_url or "not configured",
        "enam": settings.enam_source_url or "not configured",
        "note": "Use official market feeds before production deployment.",
    }
