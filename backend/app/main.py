from sqlite3 import IntegrityError

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .database import authenticate_user, create_user, init_database, list_history_records, save_history_record
from .advisory import localized_chat_answer
from .integrations import fetch_weather, integration_status, market_profile, soil_profile
from .gemini_service import gemini_service
from .ml_model import model_available
from .reports import recommendation_report
from .recommender import crop_catalog, recommend
from .schemas import ChatRequest, FarmProfile, HistoryRecord, UserCreate, UserLogin

app = FastAPI(title="Annapurna AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_database()


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


@app.post("/reports/recommendation")
def report(farm: FarmProfile):
    return Response(
        content=recommendation_report(farm),
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="annapurna-ai-report.txt"'},
    )


@app.get("/crops")
def crops():
    return {"crops": crop_catalog()}


@app.get("/admin/summary")
def admin_summary():
    return {
        "ml_model": "available" if model_available() else "not_trained",
        "history_count": len(list_history_records(1000)),
        "crop_count": len(crop_catalog()),
        "integrations": integration_status(),
    }


@app.post("/auth/register")
def register(user: UserCreate):
    try:
        return {"user": create_user(user)}
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Phone number already registered") from exc


@app.post("/auth/login")
def login(credentials: UserLogin):
    user = authenticate_user(credentials.phone, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid phone or password")
    return {"user": user}


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
def market(farm: FarmProfile):
    top = recommend(farm)[0]
    return market_profile(farm, top.crop, top.expected_profit)


@app.post("/chat")
async def chat(request: ChatRequest):
    top = recommend(request.farm)[0]
    crop = request.crop or top.crop
    answer = await gemini_service.chat_answer(request.question, crop, request.farm, top)
    if answer:
        return {"answer": answer, "provider": "gemini"}
    return {
        "answer": localized_chat_answer(crop, request.farm, top.advisory, top.rotation, top.expected_profit),
        "provider": "local_fallback",
    }


@app.post("/disease")
async def disease(file: UploadFile = File(...), crop: str | None = Form(default=None)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload a supported image file")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image is empty")
    if len(image_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be 8 MB or smaller")

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


@app.post("/history")
def save_history(record: HistoryRecord):
    return {"saved": True, "record": save_history_record(record)}


@app.get("/history")
def list_history():
    return {"history": list_history_records()}
