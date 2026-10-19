"""Weather for a farm location, from OpenWeatherMap when configured.

Two correctness rules this module enforces, both of which the earlier implementation broke:

* **Never present farmer-typed numbers as a weather reading.** With no provider configured the
  response is labelled as the farmer's own input and carries ``live: false``. A screen that says
  "Weather readiness" must not be quoting the slider the farmer just moved.
* **Never mix rainfall units.** OpenWeather's ``rain.1h`` is millimetres in the last hour.
  The crop model's ``rainfall`` is the expected seasonal total in millimetres. Substituting one for
  the other turns a drizzle into a drought signal, so recent and forecast rain are reported in
  their own fields and the seasonal input is left untouched.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from .config import settings
from .schemas import FarmProfile

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

_geocode_cache: dict[str, tuple[float, tuple[float, float, str] | None]] = {}
_weather_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_lock = asyncio.Lock()


def _cache_get(cache: dict, key: str, ttl_seconds: float):
    entry = cache.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if time.monotonic() - stored_at > ttl_seconds:
        cache.pop(key, None)
        return None
    return value


def _cache_put(cache: dict, key: str, value) -> None:
    if len(cache) > 2_000:
        cache.clear()
    cache[key] = (time.monotonic(), value)


def _advisory(temperature: float, humidity: float, rain_1h: float, rain_forecast: float) -> tuple[str, str]:
    """Return (alert, severity) from the conditions actually observed."""
    if rain_forecast >= 60:
        return "Heavy rain expected in the next five days; protect against waterlogging", "high"
    if temperature >= 42:
        return "Extreme heat; irrigate early morning and avoid midday spraying", "high"
    if temperature <= 4:
        return "Frost risk; light irrigation at night reduces damage", "high"
    if humidity >= 85 and temperature >= 20:
        return "Humid and warm; raised fungal-disease risk, scout fields this week", "moderate"
    if rain_forecast >= 15:
        return "Rain expected in the next five days; delay irrigation and spraying", "moderate"
    if humidity <= 25 and temperature >= 35:
        return "Hot and dry; evaporative stress is likely without irrigation", "moderate"
    if rain_1h > 0:
        return "Rain falling now", "low"
    return "No weather warning for the current conditions", "low"


def _offline(farm: FarmProfile, reason: str) -> dict[str, Any]:
    """The honest no-provider response: these are the farmer's own numbers, and it says so."""
    return {
        "live": False,
        "source": "farmer-entered field conditions",
        "reason": reason,
        "location": farm.location,
        "resolved_location": None,
        "temperature": farm.temperature,
        "humidity": farm.humidity,
        "recent_rain_mm_1h": None,
        "forecast_rain_mm_5d": None,
        "wind_speed_m_s": None,
        "conditions": None,
        "alert": "No live weather is connected; these are the values you entered",
        "alert_severity": "unknown",
        "observed_at": None,
        "note": "Set OPENWEATHER_API_KEY in the backend environment to replace these with a live reading.",
    }


async def _geocode(client: httpx.AsyncClient, location: str) -> tuple[float, float, str] | None:
    key = location.strip().casefold()
    cached = _cache_get(_geocode_cache, key, settings.geocode_cache_ttl_seconds)
    if cached is not None:
        return cached
    response = await client.get(
        GEOCODE_URL,
        params={
            "q": f"{location},IN" if "," not in location else location,
            "limit": 1,
            "appid": settings.openweather_api_key,
        },
    )
    response.raise_for_status()
    results = response.json()
    resolved = None
    if isinstance(results, list) and results:
        first = results[0]
        label = ", ".join(part for part in (first.get("name"), first.get("state"), first.get("country")) if part)
        resolved = (float(first["lat"]), float(first["lon"]), label)
    _cache_put(_geocode_cache, key, resolved)
    return resolved


async def _forecast_rain_mm(client: httpx.AsyncClient, lat: float, lon: float) -> float:
    """Total forecast rainfall over the next five days, in millimetres."""
    response = await client.get(
        FORECAST_URL,
        params={"lat": lat, "lon": lon, "appid": settings.openweather_api_key, "units": "metric"},
    )
    response.raise_for_status()
    payload = response.json()
    total = 0.0
    for slot in payload.get("list", []):
        rain = slot.get("rain") or {}
        # Forecast slots are 3-hourly; the key is the accumulation for that slot.
        total += float(rain.get("3h") or 0)
    return round(total, 1)


async def fetch_weather(farm: FarmProfile) -> dict[str, Any]:
    """Current conditions plus a five-day rain outlook, or a labelled offline response."""
    if not settings.openweather_api_key:
        return _offline(farm, "no weather provider is configured")
    if not farm.location.strip():
        return _offline(farm, "no location was supplied")

    cache_key = farm.location.strip().casefold()
    async with _lock:
        cached = _cache_get(_weather_cache, cache_key, settings.weather_cache_ttl_seconds)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.weather_timeout_seconds)) as client:
            resolved = await _geocode(client, farm.location)
            if resolved is None:
                return _offline(farm, f"'{farm.location}' could not be found by the weather provider")
            lat, lon, label = resolved

            current_response = await client.get(
                CURRENT_URL,
                params={"lat": lat, "lon": lon, "appid": settings.openweather_api_key, "units": "metric"},
            )
            current_response.raise_for_status()
            current = current_response.json()

            try:
                forecast_rain = await _forecast_rain_mm(client, lat, lon)
            except httpx.HTTPError:
                # The five-day outlook is an enhancement; losing it must not lose the reading.
                forecast_rain = 0.0
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            logger.warning("OpenWeather rejected the configured key")
            return _offline(farm, "the configured weather key was rejected")
        return _offline(farm, "the weather provider returned an error")
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return _offline(farm, "the weather provider could not be reached")

    main = current.get("main") or {}
    temperature = float(main.get("temp", farm.temperature))
    humidity = float(main.get("humidity", farm.humidity))
    rain_1h = float((current.get("rain") or {}).get("1h") or 0)
    conditions = (current.get("weather") or [{}])[0].get("description")
    alert, severity = _advisory(temperature, humidity, rain_1h, forecast_rain)

    result = {
        "live": True,
        "source": "OpenWeatherMap live observation",
        "reason": None,
        "location": farm.location,
        "resolved_location": label,
        "temperature": round(temperature, 1),
        "humidity": round(humidity),
        "recent_rain_mm_1h": rain_1h,
        "forecast_rain_mm_5d": forecast_rain,
        "wind_speed_m_s": round(float((current.get("wind") or {}).get("speed") or 0), 1),
        "conditions": conditions,
        "alert": alert,
        "alert_severity": severity,
        "observed_at": current.get("dt"),
        "note": (
            "Temperature and humidity are live. Seasonal rainfall in your crop plan stays as you "
            "entered it; the figures above are recent and forecast rain only."
        ),
    }
    async with _lock:
        _cache_put(_weather_cache, cache_key, result)
    return result
