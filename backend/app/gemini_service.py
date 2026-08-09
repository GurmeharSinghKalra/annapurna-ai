import json
import logging

from pydantic import BaseModel, Field

from .config import settings
from .schemas import FarmProfile, Recommendation

try:
    from google import genai
    from google.genai import types
except ImportError:  # Keeps offline tests usable before dependencies are installed.
    genai = None
    types = None


logger = logging.getLogger(__name__)


class RecommendationInsight(BaseModel):
    summary: str
    priority_action: str
    risk_note: str


class DiseaseAnalysis(BaseModel):
    prediction: str
    confidence: float = Field(ge=0, le=1)
    observations: list[str]
    advisory: str
    urgency: str


class GeminiService:
    def __init__(self) -> None:
        self.client = (
            genai.Client(api_key=settings.gemini_api_key)
            if genai is not None and settings.gemini_api_key
            else None
        )

    @property
    def available(self) -> bool:
        return self.client is not None

    async def chat_answer(
        self,
        question: str,
        crop: str,
        farm: FarmProfile,
        recommendation: Recommendation,
    ) -> str | None:
        if not self.client:
            return None

        prompt = f"""
Farmer question: {question}
Preferred response language: {farm.language}
Current crop: {crop}
Farm profile: {json.dumps(farm.model_dump(), ensure_ascii=False)}
Current recommendation: {json.dumps(recommendation.model_dump(), ensure_ascii=False)}

Answer the farmer's actual question directly. Use the farm data when relevant.
Keep the answer under 180 words, use plain language, and distinguish facts from estimates.
Do not invent live weather, market prices, diagnoses, pesticide products, or chemical dosages.
For treatment, safety, or high-cost decisions, recommend confirmation with a qualified local expert.
""".strip()

        try:
            response = await self.client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are Annapurna AI, a careful agricultural decision-support assistant for Indian farmers. "
                        "Be practical, concise, respectful, and transparent about uncertainty."
                    ),
                    max_output_tokens=500,
                ),
            )
            return response.text.strip() if response.text else None
        except Exception as exc:  # Network, quota, safety, and model errors use the local fallback.
            logger.warning("Gemini chat failed: %s", exc)
            return None

    async def recommendation_insight(
        self,
        farm: FarmProfile,
        recommendations: list[Recommendation],
    ) -> RecommendationInsight | None:
        if not self.client or not recommendations:
            return None

        candidates = [item.model_dump() for item in recommendations[:3]]
        prompt = f"""
Farm profile: {json.dumps(farm.model_dump(), ensure_ascii=False)}
Ranked crop candidates: {json.dumps(candidates, ensure_ascii=False)}

Explain why the first ranked crop is currently strongest. Refer only to supplied data.
Give one priority action and one concise risk note. Treat profit and yield as estimates.
Use the farmer's preferred language ({farm.language}) while keeping crop names recognizable.
""".strip()

        try:
            response = await self.client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You explain deterministic agricultural recommendations without changing their ranking.",
                    response_mime_type="application/json",
                    response_schema=RecommendationInsight,
                    max_output_tokens=450,
                ),
            )
            if isinstance(response.parsed, RecommendationInsight):
                return response.parsed
            if response.text:
                return RecommendationInsight.model_validate_json(response.text)
        except Exception as exc:
            logger.warning("Gemini recommendation explanation failed: %s", exc)
        return None

    async def disease_analysis(
        self,
        image_bytes: bytes,
        mime_type: str,
        crop: str | None = None,
    ) -> DiseaseAnalysis | None:
        if not self.client:
            return None

        crop_context = crop or "crop not specified"
        prompt = f"""
Review this crop image as a visual screening aid. Crop context: {crop_context}.
Identify visible symptoms and the most plausible condition, but do not claim laboratory certainty.
Return a confidence from 0 to 1, short visible observations, a conservative advisory, and urgency
as one of: low, moderate, high. Do not prescribe chemical products or dosages. If the image is
unclear or not a crop leaf, say so explicitly and lower confidence.
""".strip()

        try:
            response = await self.client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are a cautious multimodal crop-health screening assistant. "
                        "Your output supports, but never replaces, diagnosis by a qualified agriculture expert."
                    ),
                    response_mime_type="application/json",
                    response_schema=DiseaseAnalysis,
                    max_output_tokens=600,
                ),
            )
            if isinstance(response.parsed, DiseaseAnalysis):
                return response.parsed
            if response.text:
                return DiseaseAnalysis.model_validate_json(response.text)
        except Exception as exc:
            logger.warning("Gemini disease analysis failed: %s", exc)
        return None


gemini_service = GeminiService()
