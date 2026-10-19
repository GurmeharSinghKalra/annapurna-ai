from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class FarmProfile(BaseModel):
    farmer_name: str = Field(default="Demo Farmer", min_length=1, max_length=80)
    location: str = Field(default="Sonipat, Haryana", min_length=2, max_length=120)
    language: Literal["English", "Hindi", "Punjabi", "Haryanvi"] = "English"
    land_size: float = Field(default=2, ge=0.1)
    season: Literal["Kharif", "Rabi", "Annual"] = "Kharif"
    previous_crop: Literal["None", "Rice", "Maize", "Cotton", "Wheat", "Mustard", "Chickpea", "Sugarcane", "Pearl Millet"] = "None"
    soil_type: Literal["Alluvial", "Clayey", "Loamy", "Sandy loam", "Black"] = "Alluvial"
    ph: float = Field(default=6.6, ge=0, le=14)
    nitrogen: float = Field(default=62, ge=0, le=100)
    phosphorus: float = Field(default=41, ge=0, le=100)
    potassium: float = Field(default=48, ge=0, le=100)
    temperature: float = Field(default=29)
    humidity: float = Field(default=64, ge=0, le=100)
    rainfall: float = Field(default=115, ge=0)
    budget: float = Field(default=35000, ge=0)
    market_priority: Literal["Balanced", "Profit", "Sustainability", "Water saving"] = "Balanced"


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
    """A season-plan calculation; no lending, bank account, or credit data is collected."""

    farm: FarmProfile
    crop: str | None = Field(default=None, min_length=2, max_length=50)
    actual_expenses: dict[str, Annotated[float, Field(ge=0, le=10_000_000)]] = Field(default_factory=dict, max_length=12)
    market_price_per_quintal: int | None = Field(default=None, ge=1, le=1_000_000)


class PdfReportRequest(BaseModel):
    """The profile-specific analysis snapshot rendered into a downloadable PDF."""

    farm: FarmProfile
    recommendation: "Recommendation"
    weather: dict[str, Any] | None = None
    market: dict[str, Any] | None = None
    finance: dict[str, Any] | None = None


class Recommendation(BaseModel):
    crop: str
    suitability: int
    reasons: list[str]
    cautions: list[str]
    expected_profit: int
    expected_yield: int
    estimated_cost: int
    estimated_revenue: int
    profit_margin: int
    market_price: int
    market_trend: float
    sustainability_score: int
    water: str
    rotation: str
    sustainability: str
    advisory: str
