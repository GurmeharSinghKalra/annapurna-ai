import logging

import httpx

from .config import get_settings
from .schemas import FarmProfile

logger = logging.getLogger(__name__)

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
REQUEST_TIMEOUT_SECONDS = 8

MARKET_NAMES = {
    "Rice": "Paddy (common)",
    "Maize": "Maize",
    "Cotton": "Cotton",
    "Wheat": "Wheat",
    "Mustard": "Mustard seed",
    "Chickpea": "Gram",
    "Sugarcane": "Sugarcane",
    "Pearl Millet": "Bajra",
}


def integration_status() -> dict:
    settings = get_settings()
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


def _rainfall_alert(rainfall: float) -> str:
    if rainfall < 40:
        return "Low rainfall alert"
    if rainfall > 180:
        return "Waterlogging risk"
    return "Weather is workable"


def _manual_weather(farm: FarmProfile, source: str, note: str | None = None) -> dict:
    payload = {
        "source": source,
        "live": False,
        "location": farm.location,
        "temperature": farm.temperature,
        "humidity": farm.humidity,
        "seasonal_rainfall_mm": farm.rainfall,
        "recent_rainfall_mm": None,
        "alert": _rainfall_alert(farm.rainfall),
    }
    if note:
        payload["note"] = note
    return payload


def _redact(message: str) -> str:
    """Strip the API key out of httpx error text before it reaches the logs."""
    key = get_settings().openweather_api_key
    if key:
        message = message.replace(key, "***")
    return message


async def fetch_weather(farm: FarmProfile) -> dict:
    """Live weather when configured, otherwise the farmer's own readings.

    Any upstream failure degrades to the manual profile with a labelled source;
    it never propagates as a 500, and it never puts the API key in a traceback.
    """
    settings = get_settings()
    if not settings.openweather_api_key:
        return _manual_weather(farm, "manual weather fallback")

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                OPENWEATHER_URL,
                params={
                    "q": farm.location,
                    "appid": settings.openweather_api_key,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "OpenWeather returned %s for %r; using manual readings",
            exc.response.status_code,
            farm.location,
        )
        return _manual_weather(
            farm,
            "manual weather fallback",
            note=f"Live weather unavailable (HTTP {exc.response.status_code}).",
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("OpenWeather request failed: %s", _redact(str(exc)))
        return _manual_weather(
            farm, "manual weather fallback", note="Live weather unavailable (network error)."
        )

    main = payload.get("main") or {}
    weather_list = payload.get("weather") or [{}]

    # `rain.1h` is millimetres in the last hour. The crop model reasons about
    # seasonal totals, so the two are reported separately and never conflated.
    recent_rainfall = (payload.get("rain") or {}).get("1h")

    return {
        "source": "OpenWeatherMap live",
        "live": True,
        "location": farm.location,
        "temperature": main.get("temp", farm.temperature),
        "humidity": main.get("humidity", farm.humidity),
        "seasonal_rainfall_mm": farm.rainfall,
        "recent_rainfall_mm": recent_rainfall,
        "alert": weather_list[0].get("description") or _rainfall_alert(farm.rainfall),
        "note": "Seasonal rainfall stays farmer-entered; live feeds report short-interval rain only.",
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
        actions.append(
            "Maintain organic matter and repeat a laboratory soil test before the next major season."
        )

    if health_score >= 70:
        classification = "good"
    elif health_score >= 50:
        classification = "moderate"
    else:
        classification = "attention needed"

    return {
        "source": "farmer inputs with SoilGrids/ISRO-ready adapter",
        "live": False,
        "location": farm.location,
        "soil_type": farm.soil_type,
        "ph": farm.ph,
        "nitrogen": farm.nitrogen,
        "phosphorus": farm.phosphorus,
        "potassium": farm.potassium,
        "health_score": health_score,
        "classification": classification,
        "actions": actions,
        "note": "Values remain farmer-entered until coordinates or an official soil-test feed are configured.",
    }


def market_profile(farm: FarmProfile, crop: str, expected_profit: int) -> dict:
    from .recommender import CROPS

    settings = get_settings()
    crop_data = next((item for item in CROPS if item["crop"] == crop), None)
    if crop_data is None:
        raise ValueError(f"Unknown crop: {crop!r}")

    live = bool(settings.agmarknet_source_url or settings.enam_source_url)
    return {
        "source": "configured market data adapter" if live else "curated demo market profile",
        "live": live,
        "crop": crop,
        "commodity": MARKET_NAMES.get(crop, crop),
        "expected_profit": expected_profit,
        "price_band": "medium-high" if expected_profit >= 70000 else "medium",
        "modal_price_per_quintal": crop_data["market_price"],
        "trend_percent": crop_data["market_trend"],
        "trend": "rising" if crop_data["market_trend"] > 0 else "softening",
        "agmarknet": settings.agmarknet_source_url or "not configured",
        "enam": settings.enam_source_url or "not configured",
        "note": "Planning baseline; verify the current mandi price before sale or investment.",
    }
