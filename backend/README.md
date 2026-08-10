# Backend module

`backend/` is the FastAPI service that turns a farmer profile into a traceable crop plan. It owns account storage, history persistence, the optional scikit-learn model, Gemini integration, and adapter boundaries for weather, soil, and market services.

## Structure

| Path | Responsibility |
| --- | --- |
| `app/` | API routes, schemas, recommendation logic, integrations, reports, database access, and Gemini service. |
| `data/` | Starter crop-training data and runtime SQLite database (the database is ignored by Git). |
| `models/` | Generated scikit-learn model artifacts (ignored by Git). |
| `scripts/train_model.py` | Trains the local crop classifier from the starter dataset. |
| `tests/` | FastAPI smoke and integration tests. |
| `Dockerfile` | Container image definition for the API. |

## Main workflow

`POST /analysis` accepts a `FarmProfile`, obtains weather when configured, calculates soil health and actions, ranks crops with rotation context, derives economic and sustainability metrics, builds market outlooks, and asks Gemini to explain the final deterministic ranking when a key is available.

Every external dependency has a labelled fallback. The API never presents a manual or curated planning value as a live official feed.

## Environment

Create a local `.env` at the repository root. It is ignored by Git.

```dotenv
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-3.6-flash
OPENWEATHER_API_KEY=optional_key
AGMARKNET_SOURCE_URL=optional_official_feed
ENAM_SOURCE_URL=optional_official_feed
```

## Run and test

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\train_model.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
.\.venv\Scripts\python.exe -m pytest
```

The tests disable live Gemini calls so they stay deterministic and do not consume API quota. Gemini behaviour is exercised through mocked structured responses.
