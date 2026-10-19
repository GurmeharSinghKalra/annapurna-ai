"""Annapurna AI HTTP API.

Route groups:

* planning   - /recommendations, /analysis, /finance/season-plan, /weather, /soil, /market
* advisory   - /chat, /disease  (Gemini-backed, rate limited)
* reports    - /reports/recommendation, /reports/pdf
* accounts   - /auth/*          (see routers.auth)
* records    - /plans, /finance/plans, /profiles  (see routers.records)
* operations - /health, /readyz, /crops, /integrations/status, /admin/summary

Every planning route works without an account. An account only adds durable storage.
"""

from __future__ import annotations

import logging
import time
import uuid
import warnings
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import BytesIO

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from . import db as database
from .advisory import localized_chat_answer
from .config import settings
from .crop_data import provenance
from .db import Base, engine
from .deps import SessionDep, rate_limit
from .finance import UnknownExpenseCategory, season_financial_plan
from .gemini_service import gemini_service
from .integrations import integration_status, soil_profile
from .market_data import LiveMarketDataUnavailable, market_price, prices_for
from .ml_model import model_report
from .recommender import crop_catalog, recommend
from .reports import pdf_report, recommendation_report
from .routers import auth as auth_router
from .routers import records as records_router
from .schemas import ChatRequest, FarmProfile, FinancialPlanRequest, PdfReportRequest
from .weather import fetch_weather

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
)
logger = logging.getLogger("annapurna.api")

SUPPORTED_DISEASE_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_DISEASE_IMAGE_BYTES = 8 * 1024 * 1024
MAX_DISEASE_IMAGE_PIXELS = 20_000_000
MAX_DISEASE_MULTIPART_BYTES = MAX_DISEASE_IMAGE_BYTES + (128 * 1024)

# Largest request body accepted per route. Without these the only ceiling is the reverse proxy's,
# and routes that render (PDF) or decode (image) attacker-sized input become a denial of service.
MAX_JSON_BODY_BYTES = 256 * 1024
BODY_LIMITS = {
    "/disease": MAX_DISEASE_MULTIPART_BYTES,
    "/reports/pdf": MAX_JSON_BODY_BYTES,
    "/reports/recommendation": MAX_JSON_BODY_BYTES,
    "/analysis": MAX_JSON_BODY_BYTES,
    "/recommendations": MAX_JSON_BODY_BYTES,
    "/finance/season-plan": MAX_JSON_BODY_BYTES,
    "/chat": MAX_JSON_BODY_BYTES,
}


def _too_large(limit: int, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content={"detail": f"Request body must be {limit // 1024} KB or smaller"},
        headers={"X-Request-ID": request_id},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        # Convenience for local development and the portable build. Hosted deployments run
        # `alembic upgrade head` instead, and AUTO_CREATE_TABLES defaults off in production.
        from . import models  # noqa: F401  - registers every table before create_all

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        logger.info("Database schema ensured (AUTO_CREATE_TABLES is on)")
    if not await database.ping():
        logger.error("Database at %s is not reachable; account and record routes will fail", _safe_db_label())
    yield
    await database.dispose()


def _safe_db_label() -> str:
    """Describe the database without ever logging its credentials."""
    url = settings.database_url
    if url.startswith("sqlite"):
        return "sqlite"
    host = url.rsplit("@", 1)[-1] if "@" in url else "configured host"
    return f"postgresql://{host}"


app = FastAPI(
    title="Annapurna AI API",
    version="1.0.0",
    description="Crop planning, season finance, and agricultural advisory for Indian smallholders.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,  # Tokens travel in the Authorization header, never in cookies.
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID", "Retry-After"],
)


@app.middleware("http")
async def observability(request: Request, call_next):
    """Attach a request id, time the request, and never leak an internal error to the caller."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id

    limit = BODY_LIMITS.get(request.url.path)
    if limit is not None and request.method == "POST":
        try:
            declared = int(request.headers.get("content-length", "0"))
        except ValueError:
            declared = 0
        if declared > limit:
            return _too_large(limit, request_id)
        if not declared:
            # A chunked request declares no length, so the guard above is simply absent. Counting
            # bytes as they arrive is the only cap that actually holds, and without it an
            # anonymous caller can stream an unbounded body into the process.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > limit:
                    return _too_large(limit, request_id)
            request._body = bytes(body)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        logger.exception(
            "request_id=%s %s %s failed after %.0fms", request_id, request.method, request.url.path, elapsed
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Something went wrong on our side. Please try again.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
    elapsed = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    log = logger.warning if elapsed > 3_000 else logger.info
    log(
        "request_id=%s %s %s -> %s in %.0fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


app.include_router(auth_router.router)
app.include_router(records_router.router)

AiLimit = Depends(rate_limit("ai", limit=settings.ai_rate_limit_per_hour, window_seconds=3600))
PlanLimit = Depends(rate_limit("planning", limit=settings.analysis_rate_limit_per_hour, window_seconds=3600))


# --------------------------------------------------------------------------- operations


@app.get("/health", tags=["operations"])
async def health() -> dict:
    """Liveness plus a description of which capabilities are actually available."""
    return {
        "status": "ok",
        "service": "annapurna-ai",
        "version": app.version,
        "environment": settings.app_env,
        "ml_model": model_report()["status"],
        "generative_ai": "configured" if gemini_service.available else "local_fallback",
        "live_weather": "configured" if settings.openweather_api_key else "not_configured",
        "live_market": "configured" if settings.agmarknet_api_key else "not_configured",
        "database": _safe_db_label(),
        "rate_limiter": "in-process (single replica only)",
    }


@app.get("/readyz", tags=["operations"])
async def readyz() -> Response:
    """Readiness: fails when a dependency the API cannot serve without is down."""
    database_ok = await database.ping()
    payload = {"status": "ready" if database_ok else "degraded", "database": "ok" if database_ok else "unreachable"}
    return JSONResponse(
        payload,
        status_code=status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.get("/crops", tags=["operations"])
def crops() -> dict:
    return {"crops": crop_catalog(), "provenance": provenance()}


@app.get("/integrations/status", tags=["operations"])
def integrations() -> dict:
    return integration_status()


@app.get("/admin/summary", tags=["operations"])
def admin_summary() -> dict:
    return {
        "ml_model": model_report(),
        "crop_count": len(crop_catalog()),
        "crop_data": provenance(),
        "integrations": integration_status(),
    }


# --------------------------------------------------------------------------- planning


@app.post("/recommendations", tags=["planning"], dependencies=[PlanLimit])
async def crop_recommendations(farm: FarmProfile, session: SessionDep) -> dict:
    prices, price_notes = await prices_for(session, [item["crop"] for item in crop_catalog()], farm.location)
    recommendations = recommend(farm, prices)[:5]
    insight = await gemini_service.recommendation_insight(farm, recommendations)
    return {
        "recommendations": recommendations,
        "ai_explanation": insight.model_dump() if insight else None,
        # "local_fallback" named a fallback that does not exist: the field was simply null.
        "ai_provider": "gemini" if insight else "none",
        "ai_provider_note": None if insight else "An AI explanation needs GEMINI_API_KEY to be configured.",
        "price_source": "live mandi prices where available" if prices else "announced support prices",
        "price_notes": price_notes,
    }


@app.post("/analysis", tags=["planning"], dependencies=[PlanLimit])
async def farm_analysis(farm: FarmProfile, session: SessionDep) -> dict:
    """The full workflow: weather, soil, ranked crops, rotation, market and an AI explanation.

    Live weather is reported, never scored. The crop bands are whole-season means, while the
    provider returns one instant: substituting it made the same farm rank differently depending
    on the hour it was asked. A 15C morning reading scored Maize first and Rice fifth; a 44C
    afternoon reading reversed it. The farmer's own seasonal figures are what get ranked, and
    the live observation is returned alongside for the weather panel and short-horizon advice.
    """
    weather_data = await fetch_weather(farm)
    analysed_farm = farm

    prices, price_notes = await prices_for(session, [item["crop"] for item in crop_catalog()], farm.location)
    recommendations = recommend(analysed_farm, prices)[:5]

    markets = []
    for item in recommendations[:3]:
        try:
            markets.append(await market_price(session, item.crop, farm.location))
        except LiveMarketDataUnavailable as exc:
            markets.append(
                {
                    "source": "no live mandi price available",
                    "live": False,
                    "crop": item.crop,
                    "commodity": item.crop,
                    "modal_price_per_quintal": item.market_price,
                    "price_basis": item.price_basis,
                    "trend_percent": None,
                    "trend": "unknown",
                    "note": str(exc),
                }
            )

    insight = await gemini_service.recommendation_insight(analysed_farm, recommendations)
    return {
        "analyzed_at": datetime.now(UTC).isoformat(),
        "recommendations": recommendations,
        # The exact profile the ranking used, so the UI never has to guess whether a live
        # reading replaced something the farmer entered.
        "analyzed_farm": analysed_farm.model_dump(),
        "weather": weather_data,
        "soil": soil_profile(analysed_farm),
        "markets": markets,
        "ai_explanation": insight.model_dump() if insight else None,
        "ai_provider": "gemini" if insight else "none",
        "ai_provider_note": None if insight else "An AI explanation needs GEMINI_API_KEY to be configured.",
        "crop_data": provenance(),
        "price_notes": price_notes,
        "data_note": (
            "Each section states its own source. Values marked as your input are not measurements, "
            "and support prices are not sale prices. Crop ranking uses the seasonal conditions you "
            "entered; live weather is shown for context and does not change the ranking."
        ),
    }


@app.post("/weather", tags=["planning"], dependencies=[PlanLimit])
async def weather(farm: FarmProfile) -> dict:
    return await fetch_weather(farm)


@app.post("/soil", tags=["planning"])
def soil(farm: FarmProfile) -> dict:
    return soil_profile(farm)


@app.post("/market", tags=["planning"], dependencies=[PlanLimit])
async def market(farm: FarmProfile, session: SessionDep) -> dict:
    top = recommend(farm)[0]
    try:
        return await market_price(session, top.crop, farm.location)
    except LiveMarketDataUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@app.post("/finance/season-plan", tags=["planning"], dependencies=[PlanLimit])
async def financial_plan(request: FinancialPlanRequest, session: SessionDep) -> dict:
    crops_to_price = [request.crop] if request.crop else [item["crop"] for item in crop_catalog()]
    prices, _ = await prices_for(session, crops_to_price, request.farm.location)
    try:
        return season_financial_plan(request, prices)
    except UnknownExpenseCategory as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


# --------------------------------------------------------------------------- reports


@app.post("/reports/recommendation", tags=["reports"])
async def report(farm: FarmProfile, session: SessionDep) -> Response:
    prices, _ = await prices_for(session, [item["crop"] for item in crop_catalog()], farm.location)
    return Response(
        content=recommendation_report(farm, prices),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="annapurna-ai-report.txt"'},
    )


@app.post("/reports/pdf", tags=["reports"], dependencies=[PlanLimit])
async def report_pdf(request: PdfReportRequest, session: SessionDep) -> Response:
    prices, _ = await prices_for(session, [item["crop"] for item in crop_catalog()], request.farm.location)
    try:
        # Laying out a PDF is CPU-bound and synchronous; running it inline would block the event
        # loop for every other request on this worker.
        content = await run_in_threadpool(pdf_report, request, prices)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    crop_name = request.requested_crop or "crop"
    slug = "".join(char if char.isalnum() else "-" for char in crop_name.lower()).strip("-")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="annapurna-{slug or "crop"}-report.pdf"'},
    )


# --------------------------------------------------------------------------- advisory


@app.post("/chat", tags=["advisory"], dependencies=[AiLimit])
async def chat(request: ChatRequest, session: SessionDep) -> dict:
    prices, _ = await prices_for(session, [item["crop"] for item in crop_catalog()], request.farm.location)
    ranked = recommend(request.farm, prices)
    top = ranked[0]
    crop = request.crop or top.crop
    # Answer about the crop the farmer asked about, not whichever one ranks first.
    context = next((item for item in ranked if item.crop == crop), top)

    answer = await gemini_service.chat_answer(request.question, crop, request.farm, context, request.finance)
    if answer:
        return {"answer": answer, "provider": "gemini", "crop": crop}
    return {
        "answer": localized_chat_answer(crop, request.farm, context, request.finance),
        "provider": "local_fallback",
        "crop": crop,
    }


@app.post("/disease", tags=["advisory"], dependencies=[AiLimit])
async def disease(file: UploadFile = File(...), crop: str | None = Form(default=None)) -> dict:
    if file.content_type not in SUPPORTED_DISEASE_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a PNG, JPEG, or WebP crop image",
        )
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty")
    if len(image_bytes) > MAX_DISEASE_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image must be 8 MB or smaller"
        )
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as image:
                image.verify()
            # verify() consumes the file object, so reopen before reading any attribute.
            with Image.open(BytesIO(image_bytes)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("unsupported image format")
                if image.width * image.height > MAX_DISEASE_IMAGE_PIXELS:
                    raise ValueError("image dimensions are too large")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Upload a valid PNG, JPEG, or WebP image no larger than 20 megapixels",
        ) from None

    analysis = await gemini_service.disease_analysis(image_bytes, file.content_type, crop)
    if analysis:
        return {
            "filename": file.filename,
            "status": "screening_complete",
            "provider": "gemini",
            **analysis.model_dump(),
            "disclaimer": (
                "A visual screening aid, not a diagnosis. Confirm with a qualified agriculture "
                "expert before any treatment."
            ),
        }
    # No image model is configured, so no prediction is invented. The previous version returned
    # "leaf stress detected" at 72% confidence for any image at all, including a blank one.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Crop-image screening needs GEMINI_API_KEY to be configured. No offline image model is "
            "bundled, and guessing a diagnosis would be unsafe."
        ),
    )
