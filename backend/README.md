# Backend module

`backend/` is the FastAPI service that turns a farmer profile into a traceable crop
plan. It owns accounts and sessions, history persistence, the optional scikit-learn
model, the Gemini boundary, and adapters for weather, soil, and market data.

All agronomic decisions happen here. The frontend renders results; it never ranks.

## Structure

| Path | Responsibility |
| --- | --- |
| `app/` | Routes, schemas, recommendation logic, integrations, reports, persistence, security. |
| `data/` | Starter crop-training data and the runtime SQLite database (the database is ignored by Git). |
| `models/` | Generated model artifacts and their metrics file (ignored by Git). |
| `scripts/train_model.py` | Trains the classifier and records cross-validated accuracy. |
| `tests/` | Hermetic API, recommender, auth, and model tests. |
| `Dockerfile` | Production image; runs unprivileged with a healthcheck. |
| `requirements.txt` | Runtime dependencies only. |
| `requirements-dev.txt` | Runtime plus test tooling. |

## Main workflow

`POST /analysis` accepts a `FarmProfile`, obtains weather when configured, scores
soil health, ranks crops with rotation context, derives economics and sustainability
metrics, builds market outlooks, and asks Gemini to explain — never to reorder — the
deterministic ranking.

Every external dependency has a labelled fallback, and an upstream failure degrades
to it rather than returning 5xx. The API never presents a manual or curated value as
a live official feed: each response carries `source` and `live`.

## Invariants

- `estimated_revenue == expected_yield * market_price`
- `expected_profit == estimated_revenue - estimated_cost`
- Results are totally ordered by `(-suitability, -expected_profit, crop)`
- The trained model influences ranking only above 60% cross-validated accuracy,
  scaled by that accuracy

These are enforced by tests in `tests/test_recommender.py`.

## Environment

Create `.env` at the repository root; see `docs/SETUP.md` for the full table. The
service runs with no keys set.

## Run and test

```bash
python3 -m venv .venv && . .venv/bin/activate    # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python scripts/train_model.py
python -m uvicorn app.main:app --reload --port 8000
python -m pytest -q
```

Tests use a temporary database and model directory, force API keys empty before the
app is imported, and disable live Gemini calls.
