"""Deterministic, explainable crop ranking.

What changed from the first version, and why each change matters to a farmer:

* **No score floor.** Suitability was clamped to a minimum of 36, so a field with pH 14, no
  nutrients and no rainfall still showed every crop at "36% suitable". Unsuitable crops now score
  near zero and are labelled ``not recommended``.
* **Hard limiters, not just weights.** Some conditions are disqualifying rather than merely
  unfavourable: the wrong season, soil pH well outside the crop's range, a high-water crop on a
  rainfed field. Each caps the final score and is returned in ``limiters`` so the farmer sees the
  single reason rather than an unexplained number.
* **Irrigation is an input, not an assumption.** Ranking paddy against bajra is meaningless without
  knowing whether water is assured. The earlier version silently credited every farm with the same
  irrigation allowance, which let a zero-rainfall field still score well on water.
* **Economics are ranges.** Yield and cost vary with variety, irrigation and pest year, so low /
  typical / high are all returned instead of one number that reads as a promise.
* **No invented market trend**, and yield is not rounded before the money is calculated (rounding
  first made break-even price jump non-monotonically on small plots).
"""

from __future__ import annotations

from dataclasses import dataclass

from .crop_data import CROPS, ROTATION_BENEFIT, WATER_DEMAND_RANK, Crop, Range
from .ml_model import predict_crop
from .schemas import FarmProfile, Recommendation

# Component weights, summing to 100 before rotation and model adjustments.
W_SEASON = 22
W_SOIL = 16
W_WATER = 20
W_PH = 14
W_TEMPERATURE = 12
W_NUTRIENTS = 11
W_PRIORITY = 5

W_ROTATION = 10
W_MODEL = 6

# Millimetres of irrigation a season can realistically add, on top of rainfall, by access level.
IRRIGATION_ALLOWANCE_MM = {"Rainfed": 0, "Limited": 250, "Assured": 900}

VERDICTS = (
    (78, "strong match"),
    (64, "good match"),
    (48, "workable with care"),
    (32, "marginal"),
    (0, "not recommended"),
)


@dataclass(frozen=True)
class Limiter:
    """A disqualifying condition: it caps the score no matter how well everything else fits."""

    reason: str
    cap: int


def _band_score(value: float, low: float, high: float, points: float, tolerance: float) -> float:
    """Full points inside the band, tapering linearly to zero ``tolerance`` units outside it."""
    if low <= value <= high:
        return points
    distance = low - value if value < low else value - high
    if distance >= tolerance:
        return 0.0
    return points * (1 - (distance / tolerance))


def _verdict(score: float) -> str:
    for threshold, label in VERDICTS:
        if score >= threshold:
            return label
    return "not recommended"


def seasonal_water_mm(farm: FarmProfile) -> int:
    """Water the crop can actually receive: expected rainfall plus what irrigation can add."""
    return int(farm.rainfall + IRRIGATION_ALLOWANCE_MM[farm.irrigation])


def _season(crop: Crop, farm: FarmProfile, reasons: list[str], cautions: list[str], limiters: list[Limiter]) -> float:
    if crop.season == farm.season:
        reasons.append(f"Grown in {farm.season}, the season you are planning")
        return W_SEASON
    if crop.season == "Annual":
        cautions.append(
            f"{crop.name} occupies the field for about {int(crop.duration_days.typical)} days, "
            f"well beyond one {farm.season} season"
        )
        return W_SEASON * 0.55
    limiters.append(
        Limiter(f"{crop.name} is a {crop.season} crop and cannot be sown for your {farm.season} plan", cap=25)
    )
    return 0.0


def _join(items: tuple[str, ...]) -> str:
    """'a', 'a or b', 'a, b or c' - so limiter text reads as a sentence."""
    lowered = [item.lower() for item in items]
    if len(lowered) == 1:
        return lowered[0]
    return f"{', '.join(lowered[:-1])} or {lowered[-1]}"


def _soil(crop: Crop, farm: FarmProfile, reasons: list[str], limiters: list[Limiter]) -> float:
    if farm.soil_type in crop.soils:
        reasons.append(f"{farm.soil_type} soil suits {crop.name}")
        return W_SOIL
    limiters.append(
        Limiter(
            f"{crop.name} needs {_join(crop.soils)} soil; yours is {farm.soil_type.lower()}",
            cap=62,
        )
    )
    return 0.0


def _water(crop: Crop, farm: FarmProfile, reasons: list[str], cautions: list[str], limiters: list[Limiter]) -> float:
    need_low, need_high = crop.rainfall_mm_season
    available = seasonal_water_mm(farm)
    score = _band_score(available, need_low, need_high, W_WATER, tolerance=max(need_low * 0.6, 150))

    if available < need_low:
        shortfall = need_low - available
        detail = (
            f"{crop.name} needs about {int(need_low)}-{int(need_high)} mm across the season. "
            f"Your {int(farm.rainfall)} mm rainfall plus {farm.irrigation.lower()} irrigation gives "
            f"roughly {available} mm, short by {int(shortfall)} mm"
        )
        # Missing more than 40% of a crop's water is not a caution, it is a reason not to sow it.
        if shortfall > need_low * 0.4:
            limiters.append(Limiter(detail, cap=30))
        else:
            cautions.append(detail)
    elif available > need_high * 1.5:
        cautions.append(f"Expected water ({available} mm) is well above {crop.name}'s need; drainage will matter")
    else:
        reasons.append(f"Seasonal water need of {int(need_low)}-{int(need_high)} mm is covered")

    if WATER_DEMAND_RANK[crop.water_demand] >= 3 and farm.irrigation == "Rainfed":
        limiters.append(
            Limiter(f"{crop.name} has {crop.water_demand.lower()} water demand and your field is rainfed", cap=28)
        )
    return score


def _nutrients(farm: FarmProfile, reasons: list[str], cautions: list[str], limiters: list[Limiter]) -> float:
    average = (farm.nitrogen + farm.phosphorus + farm.potassium) / 3
    if average >= 55:
        reasons.append("Soil nutrient levels are strong")
        return W_NUTRIENTS
    if average >= 40:
        reasons.append("Soil nutrient levels are workable")
        return W_NUTRIENTS * 0.6
    if average >= 25:
        cautions.append("Nutrient levels are low; budget for correction before sowing")
        return W_NUTRIENTS * 0.25
    limiters.append(
        Limiter(
            "Soil nutrient levels are very low. Correct them with a soil test before committing to any crop",
            cap=45,
        )
    )
    return 0.0


def _ph(crop: Crop, farm: FarmProfile, reasons: list[str], cautions: list[str], limiters: list[Limiter]) -> float:
    low, high = crop.ph
    score = _band_score(farm.ph, low, high, W_PH, tolerance=1.5)
    distance = max(low - farm.ph, farm.ph - high, 0.0)
    if distance == 0:
        reasons.append(f"Soil pH {farm.ph:g} is inside the {low:g}-{high:g} range")
    elif distance > 1.0:
        limiters.append(Limiter(f"Soil pH {farm.ph:g} is far outside {crop.name}'s {low:g}-{high:g} range", cap=40))
    else:
        cautions.append(f"Soil pH {farm.ph:g} is just outside the preferred {low:g}-{high:g} range")
    return score


def _temperature(
    crop: Crop, farm: FarmProfile, reasons: list[str], cautions: list[str], limiters: list[Limiter]
) -> float:
    low, high = crop.temperature_c
    score = _band_score(farm.temperature, low, high, W_TEMPERATURE, tolerance=8)
    distance = max(low - farm.temperature, farm.temperature - high, 0.0)
    if distance == 0:
        reasons.append(f"Temperature {farm.temperature:g}C suits the crop")
    elif distance > 6:
        limiters.append(
            Limiter(
                f"Temperature {farm.temperature:g}C is far outside {crop.name}'s {low:g}-{high:g}C range",
                cap=38,
            )
        )
    else:
        cautions.append(f"Temperature {farm.temperature:g}C is outside the {low:g}-{high:g}C range")
    return score


def _priority(crop: Crop, farm: FarmProfile, reasons: list[str]) -> float:
    rank = WATER_DEMAND_RANK[crop.water_demand]
    if farm.market_priority == "Profit" and crop.typical_profit_per_acre > 25_000:
        reasons.append("Among the higher typical returns per acre")
        return W_PRIORITY
    if farm.market_priority == "Sustainability" and (crop.nitrogen_fixing or rank == 1):
        reasons.append("Low water demand or soil-building, matching your sustainability priority")
        return W_PRIORITY
    if farm.market_priority == "Water saving" and rank <= 2:
        reasons.append(f"{crop.water_demand} water demand, matching your water-saving priority")
        return W_PRIORITY
    if farm.market_priority == "Balanced":
        return W_PRIORITY * 0.5
    return 0.0


def _rotation(crop: Crop, farm: FarmProfile, reasons: list[str], cautions: list[str]) -> float:
    previous = farm.previous_crop
    if previous in {"", "None"}:
        return 0.0
    if crop.name == previous:
        cautions.append(f"You grew {previous} last season; repeating it raises pest, disease and nutrient pressure")
        return -W_ROTATION
    if crop.name in ROTATION_BENEFIT.get(previous, frozenset()):
        reasons.append(f"A good rotation to follow {previous}")
        return W_ROTATION
    return 0.0


def _sustainability_score(crop: Crop, farm: FarmProfile) -> int:
    """0-100, responding to the crop and to the field it would be grown on."""
    water_points = {1: 40, 2: 30, 3: 15, 4: 5}[WATER_DEMAND_RANK[crop.water_demand]]
    nitrogen_points = 20 if crop.nitrogen_fixing else 8
    rotation_points = (
        18
        if crop.name in ROTATION_BENEFIT.get(farm.previous_crop, frozenset())
        else 0
        if crop.name == farm.previous_crop
        else 9
    )
    duration_points = 12 if crop.duration_days.typical <= 120 else 6 if crop.duration_days.typical <= 180 else 0

    # The environmental cost of a crop is not a property of the crop alone. What matters is how
    # much water has to be *extracted* to grow it here: rainfall is free, irrigation is pumped,
    # and in Haryana and Punjab that pumping is the groundwater decline this score exists to
    # discourage. So the penalty scales with the shortfall the farmer must make up, whether or
    # not they have the irrigation to make it up with.
    need_low = crop.rainfall_mm_season[0]
    shortfall = max(0, need_low - farm.rainfall)
    extraction = -min(30, int(shortfall / 40))

    # On top of that, water the crop simply cannot get is an agronomic risk, not just a cost.
    available = seasonal_water_mm(farm)
    unmet = 0 if available >= need_low else -min(15, int((need_low - available) / 40))

    total = water_points + nitrogen_points + rotation_points + duration_points + extraction + unmet + 15
    return max(0, min(100, total))


def _economics(crop: Crop, farm: FarmProfile, price_per_quintal: int) -> dict:
    """Low / typical / high revenue, cost and profit for the whole holding."""

    def scaled(value_range: Range) -> dict[str, float]:
        return {
            "low": value_range.low * farm.land_size,
            "typical": value_range.typical * farm.land_size,
            "high": value_range.high * farm.land_size,
        }

    yields = scaled(crop.yield_quintal_per_acre)
    costs = scaled(crop.cost_inr_per_acre)
    revenue = {key: value * price_per_quintal for key, value in yields.items()}
    return {
        "expected_yield_quintal": {key: round(value, 1) for key, value in yields.items()},
        "estimated_cost_inr": {key: round(value) for key, value in costs.items()},
        "estimated_revenue_inr": {key: round(value) for key, value in revenue.items()},
        # The bad case is a low yield against a high cost; the good case is the reverse.
        "expected_profit_inr": {
            "low": round(revenue["low"] - costs["high"]),
            "typical": round(revenue["typical"] - costs["typical"]),
            "high": round(revenue["high"] - costs["low"]),
        },
    }


def recommend(farm: FarmProfile, prices: dict[str, int] | None = None) -> list[Recommendation]:
    """Rank every crop for this farm.

    ``prices`` optionally maps crop name to a live modal price per quintal. When a crop is absent
    the announced reference price is used and ``price_basis`` says so, so the farmer always knows
    which number the money was calculated from.
    """
    prices = prices or {}
    predicted_crop, confidence = predict_crop(farm)
    results: list[Recommendation] = []

    for crop in CROPS:
        reasons: list[str] = []
        cautions: list[str] = []
        limiters: list[Limiter] = []

        score = (
            _season(crop, farm, reasons, cautions, limiters)
            + _soil(crop, farm, reasons, limiters)
            + _water(crop, farm, reasons, cautions, limiters)
            + _ph(crop, farm, reasons, cautions, limiters)
            + _temperature(crop, farm, reasons, cautions, limiters)
            + _nutrients(farm, reasons, cautions, limiters)
            + _priority(crop, farm, reasons)
            + _rotation(crop, farm, reasons, cautions)
        )

        if predicted_crop == crop.name and confidence > 0:
            score += W_MODEL * confidence
            reasons.insert(0, f"The trained model also selects {crop.name} for these conditions")

        score = max(0.0, min(100.0, score))
        for limiter in limiters:
            score = min(score, limiter.cap)

        price = prices.get(crop.name, crop.reference_price_per_quintal)
        price_basis = "live mandi modal price" if crop.name in prices else crop.reference_price_basis
        economics = _economics(crop, farm, price)

        typical_cost = economics["estimated_cost_inr"]["typical"]
        typical_revenue = economics["estimated_revenue_inr"]["typical"]
        typical_profit = economics["expected_profit_inr"]["typical"]

        if farm.budget < typical_cost:
            cautions.append(
                f"Your budget is below the typical cultivation cost of INR {typical_cost:,} for {farm.land_size:g} acre"
            )
        if typical_profit < 0:
            cautions.append(f"At INR {price:,}/quintal this crop does not cover its own cost")
        elif economics["expected_profit_inr"]["low"] < 0:
            cautions.append("A poor yield or a price fall would put this season at a loss")

        results.append(
            Recommendation(
                crop=crop.name,
                suitability=round(score),
                verdict=_verdict(score),
                limiters=[limiter.reason for limiter in limiters],
                reasons=reasons[:4],
                cautions=cautions[:4] or ["No significant warning from the conditions you entered"],
                expected_profit=typical_profit,
                expected_yield=round(economics["expected_yield_quintal"]["typical"], 1),
                estimated_cost=typical_cost,
                estimated_revenue=typical_revenue,
                profit_margin=round((typical_profit / typical_revenue) * 100) if typical_revenue else 0,
                market_price=price,
                price_basis=price_basis,
                economics=economics,
                duration_days=round(crop.duration_days.typical),
                sustainability_score=_sustainability_score(crop, farm),
                water=crop.water_demand,
                rotation=crop.rotation,
                sustainability=crop.sustainability,
                advisory=crop.advisory,
                sources=list(crop.sources),
            )
        )

    # Ties broken by typical profit, so the ordering is stable and defensible.
    return sorted(results, key=lambda item: (item.suitability, item.expected_profit), reverse=True)


def crop_catalog() -> list[dict]:
    from .crop_data import catalog

    return catalog()
