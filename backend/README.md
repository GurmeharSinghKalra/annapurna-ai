# Backend module

`backend/` is the FastAPI service that turns a farmer profile into a traceable crop plan. It owns the optional scikit-learn model, Gemini integration, and adapter boundaries for weather, soil, and market services. The current product intentionally has no account or shared-history API.

## Structure

| Path | Responsibility |
| --- | --- |
| `app/` | API routes, schemas, recommendation logic, integrations, reports, database access, and Gemini service. |
| `data/` | Starter crop-training data. |
| `models/` | Generated scikit-learn model artifacts (ignored by Git). |
| `scripts/train_model.py` | Trains the local crop classifier from the starter dataset. |
| `tests/` | FastAPI smoke and integration tests. |
| `Dockerfile` | Container image definition for the API. |

## Main workflow

`POST /analysis` accepts a `FarmProfile`, obtains weather when configured, calculates soil health and actions, ranks crops with rotation context, derives economic and sustainability metrics, builds market outlooks, and asks Gemini to explain the final deterministic ranking when a key is available.

`POST /finance/season-plan` converts a selected crop plan into a seasonal cost allocation, editable actual-expense comparison, cash-flow timeline, break-even price, working-capital gap, and base/downside scenarios. It is a farm-planning calculation only: it does not collect financial-account data or make lending, credit, or investment decisions.

Every external dependency has a labelled fallback. The API never presents a manual or curated planning value as a live official feed.
Crop-image screening accepts verified PNG, JPEG, or WebP files only (8 MB / 20 megapixels maximum)
before any image is sent to Gemini.

When `AGMARKNET_SOURCE_URL` or `ENAM_SOURCE_URL` is configured, the market adapter requests a
documented JSON feed contract and labels a compatible result as live. See `docs/SETUP.md`; absent,
unavailable, or incompatible feeds retain the curated planning baseline.

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
