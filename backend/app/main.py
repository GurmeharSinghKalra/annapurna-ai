import logging
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from sqlite3 import IntegrityError
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .advisory import localized_chat_answer
from .config import get_settings
from .database import (
    authenticate_user,
    count_history_records,
    count_users,
    create_session,
    create_user,
    init_database,
    list_history_records,
    resolve_session,
    revoke_session,
    save_history_record,
)
from .gemini_service import gemini_service
from .integrations import fetch_weather, integration_status, market_profile, soil_profile
from .ml_model import model_available, model_status
from .recommender import crop_catalog, recommend
from .reports import recommendation_report
from .schemas import AuthResponse, ChatRequest, FarmProfile, HistoryRecord, UserCreate, UserLogin
from .security import RateLimiter
from .uploads import read_image_upload, reject_oversized_body

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema creation belongs to application startup, not module import.
    init_database()
    yield


app = FastAPI(title="Annapurna AI API", version="1.0.0", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

bearer_scheme = HTTPBearer(auto_error=False)

login_limiter = RateLimiter(
    limit=_settings.login_attempt_limit,
    window_seconds=_settings.login_attempt_window_seconds,
)


def _client_key(request: Request, phone: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{phone}"


def _enforce_login_rate_limit(request: Request, phone: str) -> str:
    key = _client_key(request, phone)
    if not login_limiter.check(key):
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(login_limiter.retry_after(key))},
        )
    return key


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Sign in to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = resolve_session(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[dict, Depends(current_user)]


async def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints are disabled. Set ADMIN_TOKEN to enable them.",
        )
    if x_admin_token is None or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=403, detail="Invalid admin token")


# --------------------------------------------------------------------------- #
# Public metadata
# --------------------------------------------------------------------------- #


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "annapurna-ai",
        "ml_model": "available" if model_available() else "not_trained",
        "gemini": "configured" if gemini_service.available else "local_fallback",
    }


@app.get("/crops")
def crops() -> dict:
    return {"crops": crop_catalog()}


@app.get("/integrations/status")
def integrations() -> dict:
    return integration_status()


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #


@app.post("/auth/register", response_model=AuthResponse, status_code=201)
def register(user: UserCreate, request: Request) -> AuthResponse:
    _enforce_login_rate_limit(request, user.phone)
    try:
        created = create_user(user)
    except IntegrityError as exc:
        login_limiter.record_failure(_client_key(request, user.phone))
        raise HTTPException(status_code=409, detail="Phone number already registered") from exc

    token, expires_at = create_session(created["id"])
    return AuthResponse(user=created, access_token=token, expires_at=expires_at.isoformat())


@app.post("/auth/login", response_model=AuthResponse)
def login(credentials: UserLogin, request: Request) -> AuthResponse:
    key = _enforce_login_rate_limit(request, credentials.phone)

    user = authenticate_user(credentials.phone, credentials.password)
    if user is None:
        login_limiter.record_failure(key)
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    login_limiter.reset(key)
    token, expires_at = create_session(user["id"])
    return AuthResponse(user=user, access_token=token, expires_at=expires_at.isoformat())


@app.post("/auth/logout", status_code=204)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Response:
    if credentials is not None:
        revoke_session(credentials.credentials)
    return Response(status_code=204)


@app.get("/auth/me")
def me(user: CurrentUser) -> dict:
    return {"user": user}


# --------------------------------------------------------------------------- #
# Recommendations and analysis
# --------------------------------------------------------------------------- #


@app.post("/recommendations")
async def crop_recommendations(farm: FarmProfile) -> dict:
    recommendations = recommend(farm)[:5]
    insight = await gemini_service.recommendation_insight(farm, recommendations)
    return {
        "recommendations": recommendations,
        "ai_explanation": insight.model_dump() if insight else None,
        "ai_provider": "gemini" if insight else "local_fallback",
    }


@app.post("/analysis")
async def farm_analysis(farm: FarmProfile) -> dict:
    """Soil, weather, crop, rotation, market and AI workflow in one call."""
    weather_data = await fetch_weather(farm)

    # Live readings replace the corresponding farmer inputs; seasonal rainfall is
    # never overwritten, because live feeds only report short-interval rain.
    analyzed_farm = farm.model_copy(
        update={
            "temperature": weather_data["temperature"],
            "humidity": weather_data["humidity"],
        }
    )

    recommendations = recommend(analyzed_farm)[:5]
    markets = [
        market_profile(analyzed_farm, item.crop, item.expected_profit)
        for item in recommendations[:3]
    ]
    insight = await gemini_service.recommendation_insight(analyzed_farm, recommendations)

    return {
        "analyzed_at": datetime.now(UTC).isoformat(),
        "recommendations": recommendations,
        "weather": weather_data,
        "soil": soil_profile(analyzed_farm),
        "markets": markets,
        "ai_explanation": insight.model_dump() if insight else None,
        "ai_provider": "gemini" if insight else "local_fallback",
        "inputs_used": {
            "temperature": analyzed_farm.temperature,
            "humidity": analyzed_farm.humidity,
            "rainfall": analyzed_farm.rainfall,
            "temperature_source": "live" if weather_data["live"] else "farmer",
            "humidity_source": "live" if weather_data["live"] else "farmer",
            "rainfall_source": "farmer",
        },
        "data_note": "Live sources are used when configured; every fallback is labelled in its source field.",
    }


@app.post("/reports/recommendation")
def report(farm: FarmProfile) -> Response:
    return Response(
        content=recommendation_report(farm),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="annapurna-ai-report.txt"'},
    )


@app.post("/weather")
async def weather(farm: FarmProfile) -> dict:
    return await fetch_weather(farm)


@app.post("/soil")
def soil(farm: FarmProfile) -> dict:
    return soil_profile(farm)


@app.post("/market")
def market(farm: FarmProfile) -> dict:
    top = recommend(farm)[0]
    return market_profile(farm, top.crop, top.expected_profit)


@app.post("/chat")
async def chat(request: ChatRequest) -> dict:
    top = recommend(request.farm)[0]
    crop = request.crop or top.crop
    answer = await gemini_service.chat_answer(request.question, crop, request.farm, top)
    if answer:
        return {"answer": answer, "provider": "gemini"}
    return {
        "answer": localized_chat_answer(
            crop, request.farm, top.advisory, top.rotation, top.expected_profit
        ),
        "provider": "local_fallback",
    }


@app.post("/disease")
async def disease(
    request: Request,
    file: UploadFile = File(...),
    crop: str | None = Form(default=None),
) -> dict:
    settings = get_settings()
    reject_oversized_body(request.headers.get("content-length"), settings.max_upload_bytes)
    image_bytes, detected_mime = await read_image_upload(file, settings.max_upload_bytes)

    analysis = await gemini_service.disease_analysis(image_bytes, detected_mime, crop)
    if analysis:
        return {
            "filename": file.filename,
            "status": "screening_complete",
            "provider": "gemini",
            "image_type": detected_mime,
            **analysis.model_dump(),
        }
    return {
        "filename": file.filename,
        "status": "local_fallback",
        "provider": "local_fallback",
        "image_type": detected_mime,
        "prediction": "no automated screening available",
        "confidence": 0.0,
        "observations": ["Image received; Gemini is unavailable for visual analysis"],
        "advisory": (
            "This image was not analysed. Configure Gemini for screening, and confirm any "
            "suspected disease with a local agriculture expert."
        ),
        "urgency": "unknown",
    }


# --------------------------------------------------------------------------- #
# Per-farmer history
# --------------------------------------------------------------------------- #


@app.post("/history", status_code=201)
def save_history(record: HistoryRecord, user: CurrentUser) -> dict:
    return {"saved": True, "record": save_history_record(record, user_id=user["id"])}


@app.get("/history")
def list_history(user: CurrentUser) -> dict:
    return {"history": list_history_records(user_id=user["id"])}


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #


@app.get("/admin/summary", dependencies=[Depends(require_admin)])
def admin_summary() -> dict:
    return {
        "ml_model": model_status(),
        "history_count": count_history_records(),
        "user_count": count_users(),
        "crop_count": len(crop_catalog()),
        "integrations": integration_status(),
    }
