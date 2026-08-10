from .schemas import FarmProfile, Recommendation
from .ml_model import predict_crop


CROPS = [
    {
        "crop": "Rice",
        "season": "Kharif",
        "soils": ["Alluvial", "Clayey"],
        "rainfall": [140, 300],
        "temperature": [22, 36],
        "ph": [5.5, 7],
        "water": "High",
        "base_profit": 42000,
        "cost": 32000,
        "market_price": 2350,
        "market_trend": 2.4,
        "yield": 28,
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
        "base_profit": 36000,
        "cost": 26000,
        "market_price": 2250,
        "market_trend": 4.1,
        "yield": 24,
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
        "base_profit": 52000,
        "cost": 39000,
        "market_price": 7100,
        "market_trend": -1.2,
        "yield": 16,
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
        "base_profit": 38500,
        "cost": 28500,
        "market_price": 2425,
        "market_trend": 1.8,
        "yield": 25,
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
        "base_profit": 33000,
        "cost": 22000,
        "market_price": 5650,
        "market_trend": 3.3,
        "yield": 11,
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
        "base_profit": 34500,
        "cost": 23500,
        "market_price": 5900,
        "market_trend": 2.7,
        "yield": 13,
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
        "base_profit": 65000,
        "cost": 62000,
        "market_price": 360,
        "market_trend": 0.9,
        "yield": 360,
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
        "base_profit": 28000,
        "cost": 18500,
        "market_price": 2650,
        "market_trend": 5.2,
        "yield": 15,
        "rotation": "Rotate with mustard, chickpea, or wheat.",
        "sustainability": "Climate-resilient crop for low-rainfall regions.",
        "advisory": "Good fallback when rainfall is uncertain and soil is lighter.",
    },
]

LEGUMES = {"Chickpea"}
HIGH_WATER = {"Rice", "Sugarcane"}
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


def _range_score(label: str, value: float, target: list[float], points: int, reasons: list[str], cautions: list[str]) -> float:
    if target[0] <= value <= target[1]:
        reasons.append(f"{label} is in range")
        return points
    cautions.append(f"{label} is outside ideal range")
    distance = target[0] - value if value < target[0] else value - target[1]
    return -min(points, distance / 2)


def recommend(farm: FarmProfile) -> list[Recommendation]:
    predicted_crop, confidence = predict_crop(farm)
    results: list[Recommendation] = []
    for crop in CROPS:
        score = 30.0
        reasons: list[str] = []
        cautions: list[str] = []

        if crop["season"] == farm.season or crop["season"] == "Annual":
            score += 18
            reasons.append(f"Fits {farm.season} planning")
        else:
            cautions.append(f"Usually grown in {crop['season']}")

        if farm.soil_type in crop["soils"]:
            score += 16
            reasons.append(f"{farm.soil_type} soil is suitable")
        else:
            cautions.append(f"Soil match is weaker for {farm.soil_type}")

        score += _range_score("pH", farm.ph, crop["ph"], 12, reasons, cautions)
        score += _range_score("temperature", farm.temperature, crop["temperature"], 10, reasons, cautions)
        score += _range_score("rainfall", farm.rainfall, crop["rainfall"], 12, reasons, cautions)

        nutrients = (farm.nitrogen + farm.phosphorus + farm.potassium) / 3
        if nutrients >= 55:
            score += 10
            reasons.append("Nutrient level is strong")
        elif nutrients >= 40:
            score += 6
            reasons.append("Nutrient level is workable")
        else:
            cautions.append("Nutrient correction is needed")

        if farm.market_priority == "Profit" and crop["base_profit"] > 40000:
            score += 6
        if farm.market_priority == "Sustainability" and crop["water"] == "Low":
            score += 7
        if farm.market_priority == "Water saving" and crop["water"] in ["Low", "Medium"]:
            score += 7
        if farm.previous_crop not in {"", "None"}:
            if crop["crop"] in ROTATION_MATCHES.get(farm.previous_crop, set()):
                score += 8
                reasons.append(f"Good rotation after {farm.previous_crop}")
            elif crop["crop"] == farm.previous_crop:
                score -= 9
                cautions.append("Repeating the previous crop can increase pest and nutrient pressure")
        if predicted_crop == crop["crop"]:
            score += 8 + (confidence * 6)
            reasons.insert(0, "ML model selected this crop")

        suitability = int(max(36, min(98, round(score))))
        budget_factor = 1 if farm.budget >= crop["base_profit"] * 0.55 else 0.86
        estimated_cost = round(crop["cost"] * farm.land_size)
        expected_profit = round(crop["base_profit"] * farm.land_size * budget_factor)
        estimated_revenue = estimated_cost + expected_profit
        profit_margin = round((expected_profit / estimated_revenue) * 100) if estimated_revenue else 0
        water_score = {"Low": 28, "Medium": 21, "High": 12, "Very high": 6}[crop["water"]]
        rotation_score = 12 if crop["crop"] in ROTATION_MATCHES.get(farm.previous_crop, set()) else 7
        nitrogen_score = 10 if crop["crop"] in LEGUMES else 6
        sustainability_score = min(96, 45 + water_score + rotation_score + nitrogen_score)
        results.append(
            Recommendation(
                crop=crop["crop"],
                suitability=suitability,
                reasons=reasons[:4],
                cautions=cautions[:3] or ["No major warning from current inputs"],
                expected_profit=expected_profit,
                expected_yield=round(crop["yield"] * farm.land_size),
                estimated_cost=estimated_cost,
                estimated_revenue=estimated_revenue,
                profit_margin=profit_margin,
                market_price=crop["market_price"],
                market_trend=crop["market_trend"],
                sustainability_score=sustainability_score,
                water=crop["water"],
                rotation=crop["rotation"],
                sustainability=crop["sustainability"],
                advisory=crop["advisory"],
            )
        )

    return sorted(results, key=lambda item: item.suitability, reverse=True)


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
        }
        for crop in CROPS
    ]
