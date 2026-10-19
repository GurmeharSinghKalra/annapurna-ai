"""Soil interpretation and external-integration status.

Weather lives in ``weather`` and mandi prices in ``market_data``. This module keeps the soil
assessment, which is computed from farmer input, and the single honest account of which external
services are actually connected.
"""

from __future__ import annotations

from .config import settings
from .gemini_service import gemini_service
from .market_data import LiveMarketDataUnavailable  # re-exported for callers and tests
from .schemas import FarmProfile

__all__ = ["LiveMarketDataUnavailable", "integration_status", "soil_profile"]

# Soil-test index bands used by Indian state soil-health-card guidance (relative 0-100 scale).
NUTRIENT_BANDS = ((0, 25, "very low"), (25, 40, "low"), (40, 55, "medium"), (55, 75, "sufficient"), (75, 101, "high"))


def _band(value: float) -> str:
    for low, high, label in NUTRIENT_BANDS:
        if low <= value < high:
            return label
    return "high"


def integration_status() -> dict:
    """Which external services are connected right now.

    Every value is derived from configuration that is actually read at request time. A service
    with no implementation behind it is reported as ``not_implemented`` rather than dressed up as
    "adapter_ready", which told an operator nothing and implied a capability that did not exist.
    """
    return {
        "weather": {
            "provider": "OpenWeatherMap",
            "status": "connected" if settings.openweather_api_key else "no_api_key",
            "effect": (
                "Live temperature, humidity and a five-day rain outlook."
                if settings.openweather_api_key
                else "Weather screens show the values you typed, labelled as your own input."
            ),
        },
        "market": {
            "provider": "AGMARKNET daily mandi prices (data.gov.in)",
            "status": "connected" if settings.agmarknet_api_key else "no_api_key",
            "effect": (
                "Crop economics use the current modal price for your district."
                if settings.agmarknet_api_key
                else "Crop economics use announced support prices, clearly labelled as MSP, not a sale price."
            ),
        },
        "generative_ai": {
            "provider": "Google Gemini",
            "status": "connected" if settings.gemini_api_key else "no_api_key",
            "model": gemini_service.active_model or settings.gemini_model,
            "effect": (
                "Recommendation explanations, multilingual advisory chat and crop-image screening."
                if settings.gemini_api_key
                else "Advisory chat uses a fixed local template; image screening is unavailable."
            ),
        },
        "soil": {
            "provider": "Farmer-entered values",
            "status": "farmer_input",
            "effect": "pH and NPK come from the planner form. No soil-test or satellite feed is connected.",
        },
        "satellite": {
            "provider": "ISRO Bhuvan / SoilGrids",
            "status": "not_implemented",
            "effect": "No code calls these services. Listed because the roadmap targets them.",
        },
        "database": {
            "provider": "PostgreSQL" if settings.database_url.startswith("postgres") else "SQLite",
            "status": "configured",
            "effect": "Accounts, saved plans, season budgets and the mandi price cache.",
        },
    }


def soil_profile(farm: FarmProfile) -> dict:
    """Interpret the farmer's soil readings into a score and specific next actions."""
    nitrogen_band = _band(farm.nitrogen)
    phosphorus_band = _band(farm.phosphorus)
    potassium_band = _band(farm.potassium)

    nutrient_average = (farm.nitrogen + farm.phosphorus + farm.potassium) / 3
    # 6.5-7.5 is the broad optimum for the crops in this catalogue; score falls away either side.
    ph_distance = max(6.5 - farm.ph, farm.ph - 7.5, 0.0)
    ph_score = max(0.0, 100 - (ph_distance * 28))
    health_score = round((nutrient_average * 0.55) + (ph_score * 0.45))

    actions: list[str] = []
    if farm.ph < 5.5:
        actions.append(
            "Strongly acidic soil. Agricultural lime is usually needed; ask a soil-testing lab for "
            "the rate, because over-liming is as damaging as under-liming."
        )
    elif farm.ph < 6.0:
        actions.append("Mildly acidic. Lime may help; confirm the rate against a laboratory soil test.")
    elif farm.ph > 8.5:
        actions.append(
            "Strongly alkaline or sodic soil. Gypsum plus organic matter is the usual correction, "
            "and it takes more than one season. Consult your state agriculture office first."
        )
    elif farm.ph > 7.8:
        actions.append("Mildly alkaline. Add organic matter and prefer tolerant crops such as mustard or bajra.")

    if nitrogen_band in {"very low", "low"}:
        actions.append(
            f"Nitrogen is {nitrogen_band}. Split the dose across growth stages, and consider a "
            "legume such as chickpea in the rotation to rebuild it."
        )
    if phosphorus_band in {"very low", "low"}:
        actions.append(f"Phosphorus is {phosphorus_band}. Apply as a basal dose; confirm the rate with a soil test.")
    if potassium_band in {"very low", "low"}:
        actions.append(
            f"Potassium is {potassium_band}. It drives water-stress tolerance, so correcting it "
            "matters most where irrigation is uncertain."
        )
    if not actions:
        actions.append(
            "No correction is indicated by these readings. Keep organic matter up and repeat a "
            "laboratory soil test before the next major season."
        )

    return {
        "source": "farmer-entered soil readings",
        "live": False,
        "location": farm.location,
        "soil_type": farm.soil_type,
        "ph": farm.ph,
        "ph_classification": (
            "strongly acidic"
            if farm.ph < 5.5
            else "acidic"
            if farm.ph < 6.5
            else "neutral"
            if farm.ph <= 7.5
            else "alkaline"
            if farm.ph <= 8.5
            else "strongly alkaline"
        ),
        "nutrients": {
            "nitrogen": {"value": farm.nitrogen, "band": nitrogen_band},
            "phosphorus": {"value": farm.phosphorus, "band": phosphorus_band},
            "potassium": {"value": farm.potassium, "band": potassium_band},
        },
        "health_score": max(0, min(100, health_score)),
        "classification": "good" if health_score >= 70 else "moderate" if health_score >= 50 else "attention needed",
        "actions": actions,
        "note": (
            "These are the values you entered, interpreted against standard soil-health bands. "
            "No soil-test laboratory or satellite feed is connected, so they are not a measurement."
        ),
    }
