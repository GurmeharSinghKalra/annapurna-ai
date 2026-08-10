"""Deterministic crop ranking.

Two rules hold everything together:

1. Money reconciles. Revenue is always `expected_yield * market_price`, cost is
   always `cost_per_acre * land_size`, and profit is the difference. No figure is
   quoted that cannot be recomputed from the two the user can see.
2. Scores use their full range. The raw score is normalised against the maximum
   attainable score rather than clipped at a ceiling, so distinct farms produce
   distinct rankings instead of piling up at the top of the scale.
"""

from .ml_model import predict_crop
from .schemas import FarmProfile, Recommendation

# Per-acre economics. `cost` and `yield_per_acre` are planning baselines; `market_price`
# is rupees per quintal. Revenue is derived, never stored, so these cannot disagree.
CROPS = [
    {
        "crop": "Rice",
        "season": "Kharif",
        "soils": ["Alluvial", "Clayey"],
        "rainfall": [140, 300],
        "temperature": [22, 36],
        "ph": [5.5, 7],
        "water": "High",
        "cost": 32000,
        "market_price": 2350,
        "market_trend": 2.4,
        "yield_per_acre": 28,
        "rotation": "Follow with lentil, pea, or mustard.",
        "sustainability": "Use alternate wetting and drying to reduce water use.",
        "advisory": "Best where water access is dependable. Watch for blast disease during humid weeks.",
    },
    {
        "crop": "Maize",
        "season": "Kharif",
        "soils": ["Alluvial", "Loamy", "Sandy loam"],
        "rainfall": [50, 120],
        "temperature": [18, 32],
        "ph": [5.8, 7.5],
        "water": "Medium",
        "cost": 26000,
        "market_price": 2250,
        "market_trend": 4.1,
        "yield_per_acre": 24,
        "rotation": "Rotate with gram, pea, or vegetables.",
        "sustainability": "Moderate water demand and good fit for diversified farms.",
        "advisory": "Avoid waterlogging and split nitrogen application across growth stages.",
    },
    {
        "crop": "Cotton",
        "season": "Kharif",
        "soils": ["Black", "Loamy"],
        "rainfall": [60, 120],
        "temperature": [21, 35],
        "ph": [6, 8],
        "water": "Medium",
        "cost": 39000,
        "market_price": 7100,
        "market_trend": -1.2,
        "yield_per_acre": 16,
        "rotation": "Rotate with wheat, gram, or sorghum.",
        "sustainability": "Needs pest monitoring; avoid repeated cotton on the same field.",
        "advisory": "Profitable but higher-risk; inspect for sucking pests and bollworm symptoms.",
    },
    {
        "crop": "Wheat",
        "season": "Rabi",
        "soils": ["Alluvial", "Loamy"],
        "rainfall": [45, 110],
        "temperature": [10, 25],
        "ph": [6, 7.8],
        "water": "Medium",
        "cost": 28500,
        "market_price": 2425,
        "market_trend": 1.8,
        "yield_per_acre": 25,
        "rotation": "Follow with mung bean, fodder, or maize.",
        "sustainability": "Works well in rotation after rice or maize.",
        "advisory": "Irrigate at crown-root initiation, tillering, and flowering.",
    },
    {
        "crop": "Mustard",
        "season": "Rabi",
        "soils": ["Loamy", "Sandy loam", "Alluvial"],
        "rainfall": [25, 75],
        "temperature": [10, 26],
        "ph": [6, 8],
        "water": "Low",
        "cost": 22000,
        "market_price": 5650,
        "market_trend": 3.3,
        "yield_per_acre": 11,
        "rotation": "Follow after rice, maize, or pearl millet.",
        "sustainability": "Good low-water option for winter season.",
        "advisory": "Protect flowering stage from aphids and avoid excess irrigation.",
    },
    {
        "crop": "Chickpea",
        "season": "Rabi",
        "soils": ["Black", "Loamy", "Sandy loam"],
        "rainfall": [30, 90],
        "temperature": [15, 30],
        "ph": [6, 8.2],
        "water": "Low",
        "cost": 23500,
        "market_price": 5900,
        "market_trend": 2.7,
        "yield_per_acre": 13,
        "rotation": "Best after wheat, rice, or maize.",
        "sustainability": "Adds nitrogen to soil and reduces fertilizer dependency.",
        "advisory": "Avoid waterlogging and use seed treatment against wilt.",
    },
    {
        "crop": "Sugarcane",
        "season": "Annual",
        "soils": ["Alluvial", "Loamy", "Black"],
        "rainfall": [110, 250],
        "temperature": [21, 38],
        "ph": [6, 8],
        "water": "Very high",
        "cost": 62000,
        "market_price": 360,
        "market_trend": 0.9,
        "yield_per_acre": 360,
        "rotation": "Rotate with pulses or vegetables after ratoon cycle.",
        "sustainability": "High return but high water footprint; use drip irrigation where possible.",
        "advisory": "Choose only when irrigation, time, and transport access are strong.",
    },
    {
        "crop": "Pearl Millet",
        "season": "Kharif",
        "soils": ["Sandy loam", "Loamy"],
        "rainfall": [25, 70],
        "temperature": [25, 40],
        "ph": [6, 8.5],
        "water": "Low",
        "cost": 18500,
        "market_price": 2650,
        "market_trend": 5.2,
        "yield_per_acre": 15,
        "rotation": "Rotate with mustard, chickpea, or wheat.",
        "sustainability": "Climate-resilient crop for low-rainfall regions.",
        "advisory": "Good fallback when rainfall is uncertain and soil is lighter.",
    },
]

LEGUMES = {"Chickpea"}
ROTATION_MATCHES = {
    "Rice": {"Chickpea", "Mustard", "Maize"},
    "Maize": {"Chickpea", "Mustard", "Wheat"},
    "Cotton": {"Wheat", "Chickpea"},
    "Wheat": {"Chickpea", "Maize", "Pearl Millet"},
    "Mustard": {"Rice", "Maize", "Pearl Millet"},
    "Chickpea": {"Rice", "Wheat", "Maize"},
    "Sugarcane": {"Chickpea", "Mustard"},
    "Pearl Millet": {"Mustard", "Chickpea", "Wheat"},
}

WATER_SUSTAINABILITY = {"Low": 28, "Medium": 21, "High": 12, "Very high": 6}

# Score budget. Agronomic fit dominates; the rest are bounded bonuses.
POINTS_SEASON = 18
POINTS_SOIL = 16
POINTS_PH = 12
POINTS_TEMPERATURE = 10
POINTS_RAINFALL = 12
POINTS_NUTRIENTS = 10
POINTS_PRIORITY = 7
POINTS_ROTATION = 8
POINTS_ML = 14

MAX_SCORE = (
    POINTS_SEASON
    + POINTS_SOIL
    + POINTS_PH
    + POINTS_TEMPERATURE
    + POINTS_RAINFALL
    + POINTS_NUTRIENTS
    + POINTS_PRIORITY
    + POINTS_ROTATION
    + POINTS_ML
)


def _range_score(
    label: str,
    value: float,
    target: list[float],
    points: int,
    reasons: list[str],
    cautions: list[str],
) -> float:
    if target[0] <= value <= target[1]:
        reasons.append(f"{label} is in range")
        return points

    distance = target[0] - value if value < target[0] else value - target[1]
    span = max(target[1] - target[0], 1e-9)
    # Penalty scales with how far outside the band the reading sits, relative to
    # the width of the band, so a 5 mm rainfall miss is not treated like a 200 mm one.
    penalty = min(points, points * (distance / span))
    cautions.append(f"{label} is outside ideal range")
    return -penalty


def _economics(crop: dict, farm: FarmProfile) -> dict:
    expected_yield = round(crop["yield_per_acre"] * farm.land_size)
    estimated_cost = round(crop["cost"] * farm.land_size)
    estimated_revenue = round(expected_yield * crop["market_price"])
    expected_profit = estimated_revenue - estimated_cost
    profit_margin = round((expected_profit / estimated_revenue) * 100) if estimated_revenue else 0
    shortfall = max(0, estimated_cost - round(farm.budget))
    return {
        "expected_yield": expected_yield,
        "estimated_cost": estimated_cost,
        "estimated_revenue": estimated_revenue,
        "expected_profit": expected_profit,
        "profit_margin": profit_margin,
        "budget_covers_cost": shortfall == 0,
        "budget_shortfall": shortfall,
    }


def recommend(farm: FarmProfile) -> list[Recommendation]:
    predicted_crop, confidence = predict_crop(farm)
    results: list[Recommendation] = []

    for crop in CROPS:
        score = 0.0
        reasons: list[str] = []
        cautions: list[str] = []

        if crop["season"] == farm.season or crop["season"] == "Annual":
            score += POINTS_SEASON
            reasons.append(f"Fits {farm.season} planning")
        else:
            cautions.append(f"Usually grown in {crop['season']}")

        if farm.soil_type in crop["soils"]:
            score += POINTS_SOIL
            reasons.append(f"{farm.soil_type} soil is suitable")
        else:
            cautions.append(f"Soil match is weaker for {farm.soil_type}")

        score += _range_score("pH", farm.ph, crop["ph"], POINTS_PH, reasons, cautions)
        score += _range_score(
            "temperature", farm.temperature, crop["temperature"], POINTS_TEMPERATURE, reasons, cautions
        )
        score += _range_score(
            "rainfall", farm.rainfall, crop["rainfall"], POINTS_RAINFALL, reasons, cautions
        )

        nutrients = (farm.nitrogen + farm.phosphorus + farm.potassium) / 3
        if nutrients >= 55:
            score += POINTS_NUTRIENTS
            reasons.append("Nutrient level is strong")
        elif nutrients >= 40:
            score += POINTS_NUTRIENTS * 0.6
            reasons.append("Nutrient level is workable")
        else:
            cautions.append("Nutrient correction is needed")

        economics = _economics(crop, farm)

        if farm.market_priority == "Profit" and economics["expected_profit"] > 0:
            # Rank on profit per acre so land size does not tilt the comparison.
            per_acre = economics["expected_profit"] / farm.land_size
            if per_acre >= 40000:
                score += POINTS_PRIORITY
            elif per_acre >= 25000:
                score += POINTS_PRIORITY * 0.6
        if farm.market_priority == "Sustainability" and crop["water"] == "Low":
            score += POINTS_PRIORITY
        if farm.market_priority == "Water saving" and crop["water"] in ("Low", "Medium"):
            score += POINTS_PRIORITY

        if farm.previous_crop != "None":
            if crop["crop"] in ROTATION_MATCHES.get(farm.previous_crop, set()):
                score += POINTS_ROTATION
                # Surfaced ahead of the agronomic reasons: the list is truncated for
                # display, and rotation is more decision-relevant than "pH is in range".
                reasons.insert(0, f"Good rotation after {farm.previous_crop}")
            elif crop["crop"] == farm.previous_crop:
                score -= POINTS_ROTATION
                cautions.append(
                    "Repeating the previous crop can increase pest and nutrient pressure"
                )

        ml_influence = "not_applied"
        if predicted_crop == crop["crop"] and confidence > 0:
            score += POINTS_ML * confidence
            reasons.insert(0, "Trained model also selected this crop")
            ml_influence = f"boosted (trust-weighted confidence {confidence:.2f})"

        if not economics["budget_covers_cost"]:
            # Do not silently promise a return the farmer cannot fund.
            shortfall_ratio = economics["budget_shortfall"] / max(economics["estimated_cost"], 1)
            score -= MAX_SCORE * 0.25 * min(1.0, shortfall_ratio)
            cautions.append(
                f"Budget is short by INR {economics['budget_shortfall']:,} of the estimated cost"
            )

        suitability = round(100 * max(0.0, min(score, MAX_SCORE)) / MAX_SCORE)

        water_score = WATER_SUSTAINABILITY[crop["water"]]
        rotation_score = (
            12 if crop["crop"] in ROTATION_MATCHES.get(farm.previous_crop, set()) else 7
        )
        nitrogen_score = 10 if crop["crop"] in LEGUMES else 6
        sustainability_score = min(96, 45 + water_score + rotation_score + nitrogen_score)

        results.append(
            Recommendation(
                crop=crop["crop"],
                suitability=suitability,
                reasons=reasons[:4],
                cautions=cautions[:3] or ["No major warning from current inputs"],
                market_price=crop["market_price"],
                market_trend=crop["market_trend"],
                sustainability_score=sustainability_score,
                water=crop["water"],
                rotation=crop["rotation"],
                sustainability=crop["sustainability"],
                advisory=crop["advisory"],
                ml_influence=ml_influence,
                **economics,
            )
        )

    # Deterministic ordering: score, then profit, then name. Never catalog order.
    return sorted(results, key=lambda item: (-item.suitability, -item.expected_profit, item.crop))


def crop_catalog() -> list[dict]:
    return [
        {
            "crop": crop["crop"],
            "season": crop["season"],
            "soils": crop["soils"],
            "water": crop["water"],
            "rainfall": crop["rainfall"],
            "temperature": crop["temperature"],
            "ph": crop["ph"],
            "market_price": crop["market_price"],
            "market_trend": crop["market_trend"],
            "cost_per_acre": crop["cost"],
            "yield_per_acre": crop["yield_per_acre"],
            "rotation": crop["rotation"],
            "sustainability": crop["sustainability"],
            "advisory": crop["advisory"],
        }
        for crop in CROPS
    ]
