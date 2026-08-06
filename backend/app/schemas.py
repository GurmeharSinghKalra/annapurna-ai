from pydantic import BaseModel, Field


class FarmProfile(BaseModel):
    farmer_name: str = Field(default="Demo Farmer")
    phone: str = Field(default="9999999999")
    location: str = Field(default="Sonipat, Haryana")
    language: str = Field(default="English")
    land_size: float = Field(default=2, ge=0.1)
    season: str = Field(default="Kharif")
    soil_type: str = Field(default="Alluvial")
    ph: float = Field(default=6.6, ge=0, le=14)
    nitrogen: float = Field(default=62, ge=0, le=100)
    phosphorus: float = Field(default=41, ge=0, le=100)
    potassium: float = Field(default=48, ge=0, le=100)
    temperature: float = Field(default=29)
    humidity: float = Field(default=64, ge=0, le=100)
    rainfall: float = Field(default=115, ge=0)
    budget: float = Field(default=35000, ge=0)
    market_priority: str = Field(default="Balanced")


class ChatRequest(BaseModel):
    question: str
    crop: str | None = None
    farm: FarmProfile


class HistoryRecord(BaseModel):
    farmer_name: str
    location: str
    crop: str
    suitability: int
    expected_profit: int


class UserCreate(BaseModel):
    name: str
    phone: str
    password: str = Field(min_length=6)
    language: str = "English"
    location: str = "Sonipat, Haryana"


class UserLogin(BaseModel):
    phone: str
    password: str


class Recommendation(BaseModel):
    crop: str
    suitability: int
    reasons: list[str]
    cautions: list[str]
    expected_profit: int
    expected_yield: int
    water: str
    rotation: str
    sustainability: str
    advisory: str
