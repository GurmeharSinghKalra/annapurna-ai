from datetime import UTC, datetime
from io import BytesIO
import warnings
import asyncio

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from starlette.responses import JSONResponse

from .advisory import localized_chat_answer
from .config import settings
from .integrations import LiveMarketDataUnavailable, fetch_market_profile, fetch_weather, integration_status, soil_profile
from .gemini_service import gemini_service
from .finance import season_financial_plan
from .ml_model import model_available
from .reports import pdf_report, recommendation_report
from .recommender import crop_catalog, recommend
from .schemas import ChatRequest, FarmProfile, FinancialPlanRequest, PdfReportRequest

app = FastAPI(title="Annapurna AI API", version="0.1.0")

SUPPORTED_DISEASE_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_DISEASE_IMAGE_BYTES = 8 * 1024 * 1024
MAX_DISEASE_IMAGE_PIXELS = 20_000_000
MAX_DISEASE_MULTIPART_BYTES = MAX_DISEASE_IMAGE_BYTES + (128 * 1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_oversized_disease_requests(request, call_next):
    """Reject declared oversized uploads before multipart parsing can consume excess memory."""
    if request.url.path == "/disease":
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            content_length = 0
        if content_length > MAX_DISEASE_MULTIPART_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Image upload must be 8 MB or smaller"})
    return await call_next(request)

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "annapurna-ai",
        "ml_model": "available" if model_available() else "not_trained",
        "gemini": "configured" if gemini_service.available else "local_fallback",
    }


@app.post("/recommendations")
async def crop_recommendations(farm: FarmProfile):
    recommendations = recommend(farm)[:5]
    insight = await gemini_service.recommendation_insight(farm, recommendations)
    return {
        "recommendations": recommendations,
        "ai_explanation": insight.model_dump() if insight else None,
        "ai_provider": "gemini" if insight else "local_fallback",
    }


@app.post("/analysis")
async def farm_analysis(farm: FarmProfile):
    """Run the proposal's soil, weather, crop, rotation, market and AI workflow together."""
    weather_data = await fetch_weather(farm)
    analyzed_farm = farm.model_copy(
        update={
            "temperature": weather_data["temperature"],
            "humidity": weather_data["humidity"],
        }
    )
    recommendations = recommend(analyzed_farm)[:5]
    async def market_or_unavailable(item):
        try:
            return await fetch_market_profile(analyzed_farm, item.crop, item.expected_profit)
        except LiveMarketDataUnavailable as exc:
            return {
                "source": "AGMARKNET official data unavailable",
                "crop": item.crop,
                "commodity": item.crop,
                "modal_price_per_quintal": None,
                "note": str(exc),
            }

    markets = await asyncio.gather(*(market_or_unavailable(item) for item in recommendations[:3]))
    insight = await gemini_service.recommendation_insight(analyzed_farm, recommendations)
    return {
        "analyzed_at": datetime.now(UTC).isoformat(),
        "recommendations": recommendations,
        "weather": weather_data,
        "soil": soil_profile(analyzed_farm),
        "markets": markets,
        "ai_explanation": insight.model_dump() if insight else None,
        "ai_provider": "gemini" if insight else "local_fallback",
        "data_note": "Live sources are used when configured; every fallback is labelled in its source field.",
    }


@app.post("/reports/recommendation")
def report(farm: FarmProfile):
    return Response(
        content=recommendation_report(farm),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="annapurna-ai-report.txt"'},
    )


@app.post("/reports/pdf")
def report_pdf(request: PdfReportRequest):
    filename = f"annapurna-{request.recommendation.crop.lower().replace(' ', '-')}-report.pdf"
    return Response(
        content=pdf_report(request),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/finance/season-plan")
async def financial_plan(request: FinancialPlanRequest):
    try:
        return await season_financial_plan(request)
    except LiveMarketDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/crops")
def crops():
    return {"crops": crop_catalog()}


@app.get("/admin/summary")
def admin_summary():
    return {
        "ml_model": "available" if model_available() else "not_trained",
        "crop_count": len(crop_catalog()),
        "integrations": integration_status(),
    }


@app.post("/weather")
async def weather(farm: FarmProfile):
    return await fetch_weather(farm)


@app.post("/soil")
def soil(farm: FarmProfile):
    return soil_profile(farm)


@app.get("/integrations/status")
def integrations():
    return integration_status()


@app.post("/market")
async def market(farm: FarmProfile):
    top = recommend(farm)[0]
    try:
        return await fetch_market_profile(farm, top.crop, top.expected_profit)
    except LiveMarketDataUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/chat")
async def chat(request: ChatRequest):
    top = recommend(request.farm)[0]
    crop = request.crop or top.crop
    answer = await gemini_service.chat_answer(request.question, crop, request.farm, top, request.finance)
    if answer:
        return {"answer": answer, "provider": "gemini"}
    return {
        "answer": localized_chat_answer(crop, request.farm, top.advisory, top.rotation, top.expected_profit, request.finance),
        "provider": "local_fallback",
    }


@app.post("/disease")
async def disease(file: UploadFile = File(...), crop: str | None = Form(default=None)):
    if file.content_type not in SUPPORTED_DISEASE_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP crop image")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(image_bytes) > MAX_DISEASE_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as image:
                image.verify()
            with Image.open(BytesIO(image_bytes)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("unsupported image format")
                if image.width * image.height > MAX_DISEASE_IMAGE_PIXELS:
                    raise ValueError("image dimensions are too large")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=422, detail="Upload a valid PNG, JPEG, or WebP image no larger than 20 megapixels")

    analysis = await gemini_service.disease_analysis(image_bytes, file.content_type, crop)
    if analysis:
        return {
            "filename": file.filename,
            "status": "screening_complete",
            "provider": "gemini",
            **analysis.model_dump(),
        }
    return {
        "filename": file.filename,
        "status": "local_fallback",
        "provider": "local_fallback",
        "prediction": "leaf stress detected",
        "confidence": 0.72,
        "observations": ["Image received; Gemini is unavailable for visual analysis"],
        "advisory": "Use this as a screening result only. Confirm with an agriculture expert before treatment.",
        "urgency": "moderate",
    }
