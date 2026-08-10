from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Season = Literal["Kharif", "Rabi", "Zaid"]
SoilType = Literal["Alluvial", "Black", "Clayey", "Loamy", "Sandy loam"]
Language = Literal["English", "Hindi", "Punjabi", "Haryanvi"]
MarketPriority = Literal["Balanced", "Profit", "Sustainability", "Water saving"]
CropName = Literal[
    "Rice", "Maize", "Cotton", "Wheat", "Mustard", "Chickpea", "Sugarcane", "Pearl Millet"
]
PreviousCrop = Literal[
    "None", "Rice", "Maize", "Cotton", "Wheat", "Mustard", "Chickpea", "Sugarcane", "Pearl Millet"
]


class FarmProfile(BaseModel):
    """Farm measurements used to rank crops.

    Every agronomic input is required. Earlier versions defaulted them, which let
    an empty request produce a confident recommendation for a farm nobody described.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity is optional: a ranking does not need to know who is asking.
    farmer_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, pattern=r"^\d{10}$")

    location: str = Field(min_length=1, max_length=160)
    language: Language = "English"
    season: Season
    previous_crop: PreviousCrop = "None"
    soil_type: SoilType
    market_priority: MarketPriority = "Balanced"

    land_size: float = Field(ge=0.1, le=10_000, description="Acres")
    ph: float = Field(ge=0, le=14)
    nitrogen: float = Field(ge=0, le=100)
    phosphorus: float = Field(ge=0, le=100)
    potassium: float = Field(ge=0, le=100)
    temperature: float = Field(ge=-20, le=60, description="Degrees Celsius")
    humidity: float = Field(ge=0, le=100)
    rainfall: float = Field(ge=0, le=5000, description="Seasonal rainfall in millimetres")
    budget: float = Field(ge=0, le=100_000_000, description="Rupees available for the season")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)
    crop: CropName | None = None
    farm: FarmProfile


class HistoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farmer_name: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=160)
    crop: CropName
    suitability: int = Field(ge=0, le=100)
    expected_profit: int


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\d{10}$")
    password: str = Field(min_length=8, max_length=256)
    language: Language = "English"
    location: str = Field(default="Sonipat, Haryana", min_length=1, max_length=160)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(pattern=r"^\d{10}$")
    password: str = Field(min_length=1, max_length=256)


class PublicUser(BaseModel):
    id: int
    name: str
    phone: str
    language: str
    location: str
    created_at: str


class AuthResponse(BaseModel):
    user: PublicUser
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: str


class Economics(BaseModel):
    """Revenue is always yield x market price, so the printed figures reconcile."""

    expected_yield: int = Field(description="Quintal across the whole holding")
    market_price: int = Field(description="Planning price per quintal, in rupees")
    estimated_revenue: int
    estimated_cost: int
    expected_profit: int
    profit_margin: int
    budget_covers_cost: bool
    budget_shortfall: int


class Recommendation(BaseModel):
    crop: CropName
    suitability: int = Field(ge=0, le=100)
    reasons: list[str]
    cautions: list[str]
    expected_profit: int
    expected_yield: int
    estimated_cost: int
    estimated_revenue: int
    profit_margin: int
    market_price: int
    market_trend: float
    budget_covers_cost: bool
    budget_shortfall: int
    sustainability_score: int = Field(ge=0, le=100)
    water: str
    rotation: str
    sustainability: str
    advisory: str
    ml_influence: str = Field(
        default="not_applied",
        description="Whether the trained classifier affected this crop's score.",
    )
