# Annapurna AI

Annapurna AI is a crop recommendation and agricultural advisory prototype for the minor project proposal. It covers the planned frontend modules and includes a backend API scaffold for the later ML/API implementation.

See `PROPOSAL_COVERAGE.md` for a requirement-by-requirement implementation map.

## Documentation

- `PROPOSAL_COVERAGE.md`: proposal requirement mapping
- `docs/SETUP.md`: local and Docker setup
- `docs/ARCHITECTURE.md`: frontend/backend architecture
- `docs/API.md`: API route reference
- `docs/TESTING.md`: automated and manual testing
- `docs/DEFENSE_GUIDE.md`: project-defense talking points
- `docs/ROADMAP.md`: next production phases

## What Is Built

- React frontend dashboard for farmer profile, soil, weather, nutrients, budget, and season inputs.
- Crop recommendation cards with suitability, reasons, warnings, yield, profit, water need, sustainability, and crop rotation.
- Weather, market, Gemini advisor, Gemini multimodal disease screening, saved history, data-source, and ethics/compliance sections.
- FastAPI backend with Gemini-powered recommendation explanations, multilingual chat, and crop-image screening.
- SQLite prototype persistence for saved recommendation history.
- Trainable scikit-learn crop recommendation pipeline with a starter dataset.
- Docker Compose setup for frontend and backend.
- PWA metadata for mobile installability.
- Text report export from the frontend recommendation screen.
- Admin/status endpoints for crop catalog, integrations, model, and history count.

## Run Frontend

```powershell
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Run Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API health check:

```text
http://127.0.0.1:8000/health
```

Useful API routes:

```text
GET  /health
GET  /crops
GET  /admin/summary
GET  /integrations/status
POST /recommendations
POST /reports/recommendation
POST /auth/register
POST /auth/login
POST /weather
POST /soil
POST /market
POST /chat
POST /disease
GET  /history
POST /history
```

## Environment

Copy `.env.example` to `.env` before Docker use or live API integration:

```powershell
Copy-Item .env.example .env
```

The app works without keys using local/manual fallbacks.

Set `GEMINI_API_KEY` to enable every generative or multimodal AI feature. `GEMINI_MODEL`
defaults to `gemini-3.6-flash` and can be changed without editing source code. Keep the key
in the backend environment only; never expose it through Vite or browser code.

## Train ML Model

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\train_model.py
```

The trained artifact is written to `backend/models/crop_recommender.joblib`. The API uses it automatically when present and falls back to rule-based scoring when it is missing.

## Next Real Integrations

- Replace rule-based recommendation with a trained scikit-learn model.
- Add OpenWeatherMap API key in backend environment variables.
- Connect Agmarknet/eNAM or a curated market dataset.
- Validate Gemini prompts and screening results with regional agriculture experts.
- Add a trained specialist disease model when a validated labelled dataset is available.

## Verify

```powershell
npm run build
cd backend
.\.venv\Scripts\python.exe scripts\train_model.py
.\.venv\Scripts\python.exe -m pytest
```

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Docker frontend:

```text
http://127.0.0.1:5174
```

Docker backend:

```text
http://127.0.0.1:8000/health
```
