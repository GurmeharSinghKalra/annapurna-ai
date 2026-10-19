"""Request and response models for the planning API."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

Season = Literal["Kharif", "Rabi", "Annual"]
Language = Literal["English", "Hindi", "Punjabi", "Haryanvi"]
SoilType = Literal["Alluvial", "Clayey", "Loamy", "Sandy loam", "Black"]
MarketPriority = Literal["Balanced", "Profit", "Sustainability", "Water saving"]
Irrigation = Literal["Rainfed", "Limited", "Assured"]
PreviousCrop = Literal["None", "Rice", "Maize", "Cotton", "Wheat", "Mustard", "Chickpea", "Sugarcane", "Pearl Millet"]


class FarmProfile(BaseModel):
    farmer_name: str = Field(default="Demo Farmer", min_length=1, max_length=80)
    location: str = Field(default="Sonipat, Haryana", min_length=2, max_length=120)
    language: Language = "English"
    # Upper bounds keep a mistyped value from producing an absurd plan: 2,000 acres is already far
    # beyond any smallholding this product is designed for.
    land_size: float = Field(default=2, ge=0.1, le=2_000, description="Holding size in acres")
    season: Season = "Kharif"
    previous_crop: PreviousCrop = "None"
    soil_type: SoilType = "Alluvial"
    irrigation: Irrigation = Field(
        default="Limited",
        description=(
            "Irrigation access. Rainfed: no assured source. Limited: a canal turn or shared "
            "borewell. Assured: own reliable source. This decides whether a high-water crop is "
            "even possible, so it cannot be inferred."
        ),
    )
    ph: float = Field(default=6.6, ge=3, le=10)
    nitrogen: float = Field(default=62, ge=0, le=100, description="Relative soil nitrogen index, 0-100")
    phosphorus: float = Field(default=41, ge=0, le=100, description="Relative soil phosphorus index, 0-100")
    potassium: float = Field(default=48, ge=0, le=100, description="Relative soil potassium index, 0-100")
    temperature: float = Field(default=29, ge=-10, le=55, description="Mean growing-season temperature, C")
    humidity: float = Field(default=64, ge=0, le=100)
    rainfall: float = Field(
        default=600,
        ge=0,
        le=5_000,
        description="Expected rainfall across the whole season, in millimetres (not per hour or per day)",
    )
    budget: float = Field(default=35_000, ge=0, le=100_000_000, description="Planning budget in INR")
    market_priority: MarketPriority = "Balanced"
    known_market_prices: dict[str, Annotated[int, Field(ge=1, le=1_000_000)]] = Field(
        default_factory=dict,
        max_length=12,
        description=(
            "Prices the farmer knows for their own mandi, as crop name to INR per quintal. "
            "These override both the live feed and the reference price, because a farmer "
            "standing in their mandi knows their realisable rate better than any national feed. "
            "This is how the product stays useful where no price feed reaches."
        ),
    )

    @field_validator("known_market_prices")
    @classmethod
    def _known_crops(cls, value: dict[str, int]) -> dict[str, int]:
        from .crop_data import CROPS_BY_NAME

        unknown = set(value) - set(CROPS_BY_NAME)
        if unknown:
            raise ValueError(
                f"Not crops this planner covers: {', '.join(sorted(unknown))}. "
                f"Valid crops: {', '.join(sorted(CROPS_BY_NAME))}"
            )
        return value

    @field_validator("farmer_name", "location")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be blank")
        return cleaned


class ValueRange(BaseModel):
    low: float
    typical: float
    high: float


class Economics(BaseModel):
    """Planning economics as ranges. A single number would read as a promise."""

    expected_yield_quintal: ValueRange
    estimated_cost_inr: ValueRange
    estimated_revenue_inr: ValueRange
    expected_profit_inr: ValueRange


class Recommendation(BaseModel):
    crop: str
    suitability: int = Field(ge=0, le=100)
    verdict: str = Field(description="strong match | good match | workable with care | marginal | not recommended")
    limiters: list[str] = Field(
        default_factory=list,
        description="Disqualifying conditions that capped the score, each on its own",
    )
    reasons: list[str]
    cautions: list[str]

    # Typical-case headline figures, drawn from `economics`.
    expected_profit: int
    expected_yield: float
    estimated_cost: int
    estimated_revenue: int
    profit_margin: int

    market_price: int
    price_basis: str = Field(description="Where market_price came from: a live mandi price or an announced MSP")
    economics: Economics
    duration_days: int
    sustainability_score: int = Field(ge=0, le=100)
    water: str
    rotation: str
    sustainability: str
    advisory: str
    sources: list[str] = Field(default_factory=list)


class FinanceContext(BaseModel):
    """The non-sensitive finance snapshot shared with the advisor for this chat turn."""

    crop: str
    planning_source: str
    actual_cost: int = Field(ge=0)
    expected_revenue: int = Field(ge=0)
    expected_profit: int
    break_even_price_per_quintal: int = Field(ge=0)
    working_capital_gap: int = Field(ge=0)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1200)
    crop: str | None = Field(default=None, min_length=2, max_length=50)
    farm: FarmProfile
    finance: FinanceContext | None = None


class FinancialPlanRequest(BaseModel):
    """A season-plan calculation. No lending, bank account, or credit data is collected."""

    farm: FarmProfile
    crop: str | None = Field(default=None, min_length=2, max_length=50)
    actual_expenses: dict[str, Annotated[float, Field(ge=0, le=10_000_000)]] = Field(
        default_factory=dict, max_length=12
    )
    market_price_per_quintal: int | None = Field(default=None, ge=1, le=1_000_000)
    yield_case: Literal["low", "typical", "high"] = Field(
        default="typical", description="Which end of the planning yield range to budget against"
    )


class PdfReportRequest(BaseModel):
    """A request for the branded PDF.

    The client names the crop; it does not supply the numbers. An earlier version rendered a
    client-posted ``Recommendation`` straight into an officially branded document, so anyone could
    produce an "Annapurna AI" PDF claiming any yield or profit and show it to a lender or a buyer.
    The server now recomputes the recommendation from ``farm``, and ``recommendation`` is accepted
    only so existing clients keep working: nothing but its ``crop`` name is read.
    """

    farm: FarmProfile
    crop: str | None = Field(default=None, min_length=2, max_length=50)
    recommendation: Recommendation | None = None
    weather: dict[str, Any] | None = None
    market: dict[str, Any] | None = None
    finance: dict[str, Any] | None = None

    @property
    def requested_crop(self) -> str | None:
        return self.crop or (self.recommendation.crop if self.recommendation else None)
