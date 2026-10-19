import httpx

from .config import settings
from .schemas import FarmProfile

MARKET_NAMES = {
    "Rice": "Paddy (common)", "Maize": "Maize", "Cotton": "Cotton", "Wheat": "Wheat",
    "Mustard": "Mustard seed", "Chickpea": "Gram", "Sugarcane": "Sugarcane",
    "Pearl Millet": "Bajra",
}
AGMARKNET_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_RESOURCE_URL = f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE_ID}"


class LiveMarketDataUnavailable(RuntimeError):
    """Raised when an official market price cannot be verified for the requested farm."""


def integration_status() -> dict:
    return {
        "soilgrids": "adapter_ready",
        "isro_bhuvan": "adapter_ready",
        "openweather": "configured" if settings.openweather_api_key else "missing_api_key",
        "agmarknet": "official_api_configured" if getattr(settings, "agmarknet_api_key", None) else "missing_api_key",
        "enam": "configured" if settings.enam_source_url else "placeholder_dataset",
        "gemini": "configured" if settings.gemini_api_key else "missing_api_key",
        "gemini_model": settings.gemini_model,
        "genai": "gemini" if settings.gemini_api_key else "local_advisory_fallback",
    }


def _manual_weather(farm: FarmProfile, source: str = "manual weather fallback") -> dict:
    alert = "Weather is workable"
    if farm.rainfall < 40:
        alert = "Low rainfall alert"
    elif farm.rainfall > 180:
        alert = "Waterlogging risk"
    return {
        "source": source,
        "location": farm.location,
        "temperature": farm.temperature,
        "humidity": farm.humidity,
        "rainfall": farm.rainfall,
        "alert": alert,
    }


async def fetch_weather(farm: FarmProfile) -> dict:
    if settings.openweather_api_key:
        try:
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
        except httpx.HTTPError:
            return _manual_weather(farm, "manual weather fallback (live request unavailable)")

    return _manual_weather(farm)


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
    price_band = "medium-high" if expected_profit >= 70000 else "medium"
    return {
        "source": "curated planning baseline",
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


def _market_records(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "records", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _normalise_record(record: dict) -> dict[str, object]:
    return {str(key).strip().lower().replace(" ", "_").replace("-", "_"): value for key, value in record.items()}


def _price_per_quintal(record: dict) -> int | None:
    normalised = _normalise_record(record)
    for key in ("modal_price_per_quintal", "modal_price", "modalprice", "modal_price_rs_per_quintal"):
        value = normalised.get(key)
        try:
            price = round(float(str(value).replace(",", "")))
        except (TypeError, ValueError):
            continue
        if price > 0:
            return price
    return None


def _matching_market_record(payload: object, commodity: str) -> tuple[dict, int] | None:
    commodity_key = commodity.casefold()
    for record in _market_records(payload):
        normalised = _normalise_record(record)
        record_commodity = str(normalised.get("commodity") or normalised.get("crop") or "").casefold()
        price = _price_per_quintal(record)
        if price and (not record_commodity or commodity_key in record_commodity or record_commodity in commodity_key):
            return normalised, price
    return None


def _agmarknet_location_filters(location: str) -> dict[str, str]:
    """Convert the UI's `District, State` location convention into official API filters."""
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if len(parts) < 2:
        return {}
    return {
        "filters[state]": parts[-1],
        "filters[district]": parts[-2],
    }


async def _fetch_agmarknet_profile(farm: FarmProfile, crop: str, expected_profit: int) -> dict:
    commodity = MARKET_NAMES.get(crop, crop)
    params = {
        "api-key": settings.agmarknet_api_key,
        "format": "json",
        # A small filtered page is sufficient for one farm lookup and avoids slow full-dataset reads.
        "limit": 100,
        "filters[commodity]": commodity,
        **_agmarknet_location_filters(farm.location),
    }
    try:
        async with httpx.AsyncClient(
            timeout=15,
            headers={"Accept": "application/json", "User-Agent": "Annapurna-AI/0.1"},
        ) as client:
            response = await client.get(AGMARKNET_RESOURCE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LiveMarketDataUnavailable("AGMARKNET could not be reached. Please try again shortly.") from exc

    matched = _matching_market_record(payload, commodity)
    if not matched:
        raise LiveMarketDataUnavailable(
            f"AGMARKNET has no current {commodity} price for {farm.location}. Choose a location with a reporting mandi."
        )
    record, modal_price = matched
    observed_at = record.get("arrival_date") or record.get("date") or "date not supplied"
    return {
        "source": "AGMARKNET official daily mandi price",
        "crop": crop,
        "commodity": commodity,
        "expected_profit": expected_profit,
        "modal_price_per_quintal": modal_price,
        "min_price_per_quintal": _price_per_quintal({"modal_price": record.get("min_price")}),
        "max_price_per_quintal": _price_per_quintal({"modal_price": record.get("max_price")}),
        "trend_percent": None,
        "trend": "historical series required",
        "state": record.get("state") or "state not supplied",
        "district": record.get("district") or "district not supplied",
        "market": record.get("market") or "market not supplied",
        "variety": record.get("variety") or "variety not supplied",
        "observed_at": str(observed_at),
        "note": "Official daily wholesale mandi price. Finance uses the displayed modal price; it is not a sale guarantee.",
    }


async def fetch_market_profile(farm: FarmProfile, crop: str, expected_profit: int) -> dict:
    """Read a configured JSON market feed, otherwise return the labelled planning baseline.

    Feed URLs are intentionally opt-in because public market portals do not share one stable,
    unauthenticated JSON contract. A configured endpoint must return a JSON object/list containing
    `commodity` (or `crop`) and `modal_price_per_quintal` (or `modal_price`).
    """
    if getattr(settings, "agmarknet_api_key", None):
        return await _fetch_agmarknet_profile(farm, crop, expected_profit)

    baseline = market_profile(farm, crop, expected_profit)
    for provider, source_url in (("Agmarknet", settings.agmarknet_source_url), ("eNAM", settings.enam_source_url)):
        if not source_url:
            continue
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    source_url,
                    params={"commodity": baseline["commodity"], "location": farm.location, "format": "json"},
                )
                response.raise_for_status()
            matched = _matching_market_record(response.json(), baseline["commodity"])
            if not matched:
                continue
            record, modal_price = matched
            observed_at = record.get("date") or record.get("reported_at") or record.get("updated_at") or "feed timestamp unavailable"
            return {
                **baseline,
                "source": f"{provider} live feed",
                "modal_price_per_quintal": modal_price,
                "trend_percent": 0,
                "trend": "not calculated",
                "market": record.get("market") or record.get("mandi") or "market not supplied",
                "observed_at": str(observed_at),
                "note": "Live modal price from the configured feed. Direction requires a historical series and is not calculated yet.",
            }
        except (httpx.HTTPError, ValueError, TypeError):
            continue
    if settings.agmarknet_source_url or settings.enam_source_url:
        return {
            **baseline,
            "source": "curated planning baseline (configured live feed unavailable or incompatible)",
            "note": "Configured market feed did not return a matching compatible price. Verify the mandi price before acting.",
        }
    return baseline
