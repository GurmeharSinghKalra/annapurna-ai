"""Agronomic and economic reference data for the supported crops.

Scope: irrigated North-Indian plains farming (Haryana, Punjab, western Uttar Pradesh). Figures
outside that region should not be trusted without revalidation, which is why ``REGION`` is
published through the API rather than left implicit.

Three deliberate choices:

* **Ranges, not point estimates.** A single "expected yield" number invites a farmer to treat a
  planning figure as a promise. Every yield and cost carries low / typical / high, and the API
  returns all three.
* **Reference price is an MSP, and says so.** ``reference_price_per_quintal`` is the announced
  support price for the stated season, used only when no live mandi price is available. It is never
  presented as the price the farmer will actually receive.
* **No hardcoded trend.** Price direction is measured from recorded observations in
  ``market_data``; a crop table cannot know it.

Sources are recorded per crop so a reviewer can check a number instead of trusting it. MSPs are
Cabinet-announced rates for the stated marketing season. Yields and costs are typical ranges from
state package-of-practices documents, university cost-of-cultivation studies, and state crop-cutting
reports; they vary with variety, irrigation, and season.

Last reviewed: 2026-10-19. MSPs must be rechecked each season; ``PRICE_SEASON`` records which one
these belong to.
"""

from __future__ import annotations

from dataclasses import dataclass, field

REGION = "Irrigated North-Indian plains (Haryana, Punjab, western Uttar Pradesh)"
PRICE_SEASON = "Kharif 2026-27 / Rabi 2026-27"
LAST_REVIEWED = "2026-10-19"


@dataclass(frozen=True)
class Range:
    """A planning range. ``typical`` is what a median farmer in the region achieves."""

    low: float
    typical: float
    high: float

    def as_dict(self) -> dict[str, float]:
        return {"low": self.low, "typical": self.typical, "high": self.high}


@dataclass(frozen=True)
class Crop:
    name: str
    season: str  # Kharif | Rabi | Annual
    duration_days: Range  # Sowing to harvest; Annual crops tie the field up for a year+
    soils: tuple[str, ...]
    rainfall_mm_season: tuple[float, float]  # Total water need across the season, millimetres
    temperature_c: tuple[float, float]  # Mean growing-season air temperature
    ph: tuple[float, float]
    water_demand: str  # Low | Medium | High | Very high
    yield_quintal_per_acre: Range
    cost_inr_per_acre: Range
    reference_price_per_quintal: int
    reference_price_basis: str
    nitrogen_fixing: bool
    rotation: str
    sustainability: str
    advisory: str
    sources: tuple[str, ...] = field(default_factory=tuple)

    @property
    def typical_profit_per_acre(self) -> float:
        return (self.yield_quintal_per_acre.typical * self.reference_price_per_quintal) - self.cost_inr_per_acre.typical


CROPS: tuple[Crop, ...] = (
    Crop(
        name="Rice",
        season="Kharif",
        duration_days=Range(110, 135, 160),
        soils=("Alluvial", "Clayey"),
        rainfall_mm_season=(900, 1800),
        temperature_c=(22, 36),
        ph=(5.5, 7.0),
        water_demand="Very high",
        yield_quintal_per_acre=Range(24, 28, 34),
        cost_inr_per_acre=Range(32_000, 38_000, 46_000),
        reference_price_per_quintal=2_441,
        reference_price_basis="MSP, paddy common grade, Kharif 2026-27",
        nitrogen_fixing=False,
        rotation="Follow with wheat, lentil, pea, or mustard.",
        sustainability=(
            "The highest water footprint of these crops and a major driver of groundwater decline "
            "in Haryana and Punjab. Alternate wetting and drying, or direct seeding, cuts water use."
        ),
        advisory=(
            "Only choose paddy where irrigation is dependable. Watch for blast during humid weeks, "
            "and check your state's transplanting-date rules before sowing."
        ),
        sources=(
            "CCEA Kharif MSP 2026-27 (paddy common Rs 2,441/quintal)",
            "Punjab Agricultural University Package of Practices: state average 66.7 q/ha (27 q/acre), 2024-25",
        ),
    ),
    Crop(
        name="Maize",
        season="Kharif",
        duration_days=Range(85, 100, 120),
        soils=("Alluvial", "Loamy", "Sandy loam"),
        rainfall_mm_season=(400, 700),
        temperature_c=(18, 32),
        ph=(5.8, 7.5),
        water_demand="Medium",
        yield_quintal_per_acre=Range(14, 20, 28),
        cost_inr_per_acre=Range(22_000, 27_000, 33_000),
        reference_price_per_quintal=2_400,
        reference_price_basis="MSP, maize, Kharif 2026-27 (approximate; confirm the notified rate)",
        nitrogen_fixing=False,
        rotation="Rotate with gram, pea, potato, or vegetables.",
        sustainability="Roughly a third of paddy's water demand; a practical diversification crop.",
        advisory="Avoid waterlogging and split the nitrogen across growth stages. Scout for fall armyworm.",
        sources=(
            "CCEA Kharif MSP 2026-27",
            "ICAR-IIMR and state package-of-practices yield ranges for irrigated kharif maize",
        ),
    ),
    Crop(
        name="Cotton",
        season="Kharif",
        duration_days=Range(160, 180, 210),
        # Black (regur) soil is the Deccan cotton soil. Haryana's own cotton belt - Sirsa,
        # Hisar, Fatehabad - is sandy alluvium, so listing only black and loamy soil made the
        # app tell a Sirsa cotton farmer their soil was wrong for the crop they actually grow.
        soils=("Alluvial", "Sandy loam", "Loamy", "Black"),
        rainfall_mm_season=(500, 900),
        temperature_c=(21, 35),
        ph=(6.0, 8.0),
        water_demand="Medium",
        # Kapas (seed cotton). Haryana and Punjab yields have fallen sharply under pink bollworm
        # and whitefly pressure; the earlier 16 q/acre figure in this project was 2-3x reality and
        # produced a profit estimate that no recent regional study supports.
        yield_quintal_per_acre=Range(3, 6, 10),
        cost_inr_per_acre=Range(34_000, 40_000, 48_000),
        reference_price_per_quintal=8_267,
        reference_price_basis="MSP, medium-staple kapas, cotton season 2026-27",
        nitrogen_fixing=False,
        rotation="Rotate with wheat, gram, or sorghum. Never follow cotton with cotton.",
        sustainability="Heavy pest pressure and high input use. Continuous cotton worsens both.",
        advisory=(
            "High risk in this region. Recent Haryana cost studies record average losses once pink "
            "bollworm damage is counted, so treat a profitable cotton estimate as the good-year case "
            "and plan for the bad one."
        ),
        sources=(
            "Textile Commissioner MSP order, cotton season 2026-27 (medium staple Rs 8,267/quintal)",
            "Haryana agricultural-university cost study: average cost Rs 40,024/acre against Rs 24,081/acre returns",
            "ICAR-CRIDA contingency plans, Sirsa / Hisar / Fatehabad (Western Zone HR-2): sandy alluvial soils",
        ),
    ),
    Crop(
        name="Wheat",
        season="Rabi",
        duration_days=Range(120, 140, 155),
        soils=("Alluvial", "Loamy"),
        rainfall_mm_season=(300, 500),
        temperature_c=(10, 25),
        ph=(6.0, 7.8),
        water_demand="Medium",
        yield_quintal_per_acre=Range(18, 22, 26),
        cost_inr_per_acre=Range(23_000, 28_000, 34_000),
        reference_price_per_quintal=2_585,
        reference_price_basis="MSP, wheat, Rabi marketing season 2026-27",
        nitrogen_fixing=False,
        rotation="Follow with mung bean, fodder, or maize.",
        sustainability="Reliable in rotation after paddy or maize; moderate irrigation need.",
        advisory="Irrigate at crown-root initiation, tillering, and flowering. Late sowing costs yield sharply.",
        sources=(
            "CCEA Rabi MSP 2026-27 (wheat Rs 2,585/quintal; Rs 2,610 announced for 2027-28)",
            "Haryana crop-cutting reports: 21-26 q/acre, 2024 and 2025 seasons",
        ),
    ),
    Crop(
        name="Mustard",
        season="Rabi",
        duration_days=Range(110, 130, 145),
        soils=("Loamy", "Sandy loam", "Alluvial"),
        rainfall_mm_season=(200, 400),
        temperature_c=(10, 26),
        ph=(6.0, 8.0),
        water_demand="Low",
        yield_quintal_per_acre=Range(5, 7, 10),
        cost_inr_per_acre=Range(15_000, 18_500, 23_000),
        reference_price_per_quintal=6_200,
        reference_price_basis="MSP, rapeseed and mustard, Rabi marketing season 2026-27",
        nitrogen_fixing=False,
        rotation="Follow after paddy, maize, or pearl millet.",
        sustainability="One of the best low-water rabi options where groundwater is stressed.",
        advisory="Protect the flowering stage from aphids. Excess irrigation reduces oil content.",
        sources=(
            "CCEA Rabi MSP 2026-27 (mustard Rs 6,200/quintal; Rs 6,613 announced for 2027-28)",
            "Published mustard cost-of-cultivation studies: about Rs 44,800/hectare (Rs 18,100/acre)",
        ),
    ),
    Crop(
        name="Chickpea",
        season="Rabi",
        duration_days=Range(100, 125, 150),
        soils=("Black", "Loamy", "Sandy loam"),
        rainfall_mm_season=(200, 400),
        temperature_c=(15, 30),
        ph=(6.0, 8.2),
        water_demand="Low",
        yield_quintal_per_acre=Range(4, 6, 8),
        cost_inr_per_acre=Range(16_000, 20_000, 25_000),
        reference_price_per_quintal=5_875,
        reference_price_basis="MSP, gram, Rabi marketing season 2026-27",
        nitrogen_fixing=True,
        rotation="Best after wheat, paddy, or maize.",
        sustainability=(
            "Fixes atmospheric nitrogen, cutting fertiliser need for the following crop, and needs little irrigation."
        ),
        advisory="Avoid waterlogging. Use seed treatment against wilt, and do not over-irrigate.",
        sources=(
            "CCEA Rabi MSP 2026-27 (gram Rs 5,875/quintal)",
            "State package-of-practices yield ranges for irrigated desi gram",
        ),
    ),
    Crop(
        name="Sugarcane",
        season="Annual",
        duration_days=Range(300, 365, 450),
        soils=("Alluvial", "Loamy", "Black"),
        rainfall_mm_season=(1500, 2500),
        temperature_c=(21, 38),
        ph=(6.0, 8.0),
        water_demand="Very high",
        yield_quintal_per_acre=Range(250, 300, 380),
        cost_inr_per_acre=Range(52_000, 62_000, 78_000),
        reference_price_per_quintal=360,
        reference_price_basis="Fair and Remunerative Price basis; state advised prices differ",
        nitrogen_fixing=False,
        rotation="Rotate with pulses or vegetables after the ratoon cycle.",
        sustainability="The largest water footprint here, and it occupies the field for a full year or more.",
        advisory=(
            "Choose sugarcane only with dependable irrigation, assured mill payment, and transport. "
            "Mill dues are frequently delayed, so the cash is not available at harvest."
        ),
        sources=(
            "Fair and Remunerative Price for sugarcane at 10.25% recovery; check your state advised price",
            "State package-of-practices yield ranges for plant cane",
        ),
    ),
    Crop(
        name="Pearl Millet",
        season="Kharif",
        duration_days=Range(75, 90, 105),
        soils=("Sandy loam", "Loamy"),
        rainfall_mm_season=(250, 500),
        temperature_c=(25, 40),
        ph=(6.0, 8.5),
        water_demand="Low",
        yield_quintal_per_acre=Range(6, 10, 15),
        cost_inr_per_acre=Range(9_000, 13_000, 18_000),
        reference_price_per_quintal=2_900,
        reference_price_basis="MSP, bajra, Kharif 2026-27",
        nitrogen_fixing=False,
        rotation="Rotate with mustard, chickpea, or wheat.",
        sustainability="The most climate-resilient option here: short duration, low water, tolerates heat.",
        advisory=(
            "A sound choice when rainfall is uncertain or soil is light. Mandi prices often sit below "
            "MSP outside procurement windows, so confirm your local rate."
        ),
        sources=(
            "CCEA Kharif MSP 2026-27 (bajra Rs 2,900/quintal)",
            "Rajasthan and Haryana value-chain reports: 8-15 q/acre for hybrids",
        ),
    ),
)

CROPS_BY_NAME: dict[str, Crop] = {crop.name: crop for crop in CROPS}

# Which crops meaningfully benefit from following the named previous crop. Used for rotation
# scoring; the reverse direction (repeating a crop) is penalised separately.
ROTATION_BENEFIT: dict[str, frozenset[str]] = {
    "Rice": frozenset({"Chickpea", "Mustard", "Wheat"}),
    "Maize": frozenset({"Chickpea", "Mustard", "Wheat"}),
    "Cotton": frozenset({"Wheat", "Chickpea"}),
    "Wheat": frozenset({"Chickpea", "Maize", "Pearl Millet"}),
    "Mustard": frozenset({"Rice", "Maize", "Pearl Millet"}),
    "Chickpea": frozenset({"Rice", "Wheat", "Maize"}),
    "Sugarcane": frozenset({"Chickpea", "Mustard"}),
    "Pearl Millet": frozenset({"Mustard", "Chickpea", "Wheat"}),
}

WATER_DEMAND_RANK = {"Low": 1, "Medium": 2, "High": 3, "Very high": 4}


def catalog() -> list[dict]:
    """The public crop catalogue, with every figure's basis attached."""
    return [
        {
            "crop": crop.name,
            "season": crop.season,
            "soils": list(crop.soils),
            "water": crop.water_demand,
            "duration_days": crop.duration_days.as_dict(),
            "rainfall_mm_season": list(crop.rainfall_mm_season),
            "temperature_c": list(crop.temperature_c),
            "ph": list(crop.ph),
            "yield_quintal_per_acre": crop.yield_quintal_per_acre.as_dict(),
            "cost_inr_per_acre": crop.cost_inr_per_acre.as_dict(),
            "reference_price_per_quintal": crop.reference_price_per_quintal,
            "reference_price_basis": crop.reference_price_basis,
            "nitrogen_fixing": crop.nitrogen_fixing,
            "sources": list(crop.sources),
        }
        for crop in CROPS
    ]


def provenance() -> dict:
    return {
        "region": REGION,
        "price_season": PRICE_SEASON,
        "last_reviewed": LAST_REVIEWED,
        "basis": (
            "Reference prices are announced support prices, not expected sale prices. Yields and "
            "costs are regional planning ranges, not guarantees. Live mandi prices replace the "
            "reference price whenever the market feed is configured and reachable."
        ),
    }
