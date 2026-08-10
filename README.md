# Annapurna AI

Annapurna AI is a crop recommendation and agricultural advisory application: a
React interface, FastAPI services, local persistence, explainable crop ranking, an
optional trained model, and Gemini-powered advisory workflows.

Two rules shape the design:

- **One source of advice.** All ranking happens on the server. The client renders
  what the API returned and never computes a recommendation of its own, so no two
  screens can disagree about what to plant.
- **Figures reconcile.** Revenue is always `expected yield x planning price`, and
  net return is always `revenue - estimated cost`. Every number shown can be
  recomputed from the others.

See `PROPOSAL_COVERAGE.md` for a requirement-by-requirement implementation map.

## Documentation

| Document | Use it for |
| --- | --- |
| `docs/SETUP.md` | Local and Docker setup |
| `docs/ARCHITECTURE.md` | Frontend/backend architecture and data flow |
| `docs/API.md` | API route reference, including authentication |
| `docs/TESTING.md` | Automated and manual verification |
| `docs/DEFENSE_GUIDE.md` | Project-defense talking points |
| `docs/ROADMAP.md` | Next production phases |

## What is built

- React frontend for the farmer profile, soil, weather, nutrients, budget, and season.
- One complete farm analysis joining soil health, weather, rotation-aware crop
  ranking, market outlook, yield, cost, revenue, profit margin, water demand, and
  a sustainability score.
- Token-based authentication with per-farmer saved plans.
- FastAPI backend with Gemini recommendation explanations, multilingual chat, and
  crop-image screening — each with a labelled local fallback.
- SQLite persistence for accounts, sessions, and saved history.
- A trainable scikit-learn pipeline that reports its own cross-validated accuracy
  and is excluded from ranking when that accuracy is too low to justify influence.
- Docker Compose setup, installable PWA, and text report export.

## Quick start

Requires Node.js 22+ and Python 3.13+.

**Frontend**

```bash
npm install
npm run dev
```

**Backend** (a second terminal)

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
```

```bash
cd backend && python scripts/train_model.py && python -m uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell the activation step is `.\.venv\Scripts\Activate.ps1`; every
other command is identical.

Open <http://127.0.0.1:5173>. The API health check is <http://127.0.0.1:8000/health>.

## Environment

```bash
cp .env.example .env
```

The app runs without any keys. Every unconfigured integration falls back to a
labelled local value; nothing manual is ever presented as a live official feed.

| Variable | Effect when unset |
| --- | --- |
| `GEMINI_API_KEY` | Explanations, chat, and image screening use local fallbacks |
| `OPENWEATHER_API_KEY` | Weather uses the farmer's own readings, labelled as such |
| `AGMARKNET_SOURCE_URL`, `ENAM_SOURCE_URL` | Market data uses the curated planning baseline |
| `ADMIN_TOKEN` | `/admin/summary` returns 503 |
| `CORS_ORIGINS` | Defaults to localhost ports 5173 and 5174 |
| `VITE_API_URL` | Frontend calls `http://127.0.0.1:8000` |

Keep every key in the backend environment. `VITE_API_URL` is the only value the
browser bundle sees, and Vite inlines it **at build time** — set it before
`npm run build`, not when the container starts.

## Train the model

```bash
cd backend && python scripts/train_model.py
```

This writes `models/crop_recommender.joblib` plus a metrics file recording
stratified cross-validated accuracy. The API loads the model only when that
accuracy clears 60%, and scales its influence by the measured value. The starter
dataset is 24 rows and scores around 0.63 — enough to demonstrate the pipeline,
not enough to rely on. Replace it with validated regional data before production.

## Verify

```bash
npm run lint && npm run build
```

```bash
cd backend && python scripts/train_model.py && python -m pytest -q
```

```bash
docker compose build && docker compose up -d --wait && curl -sf http://127.0.0.1:5174/dashboard > /dev/null && echo ok
```

CI runs all three on every push (`.github/workflows/ci.yml`).

## Docker

```bash
cp .env.example .env && docker compose up --build
```

Frontend: <http://127.0.0.1:5174> · Backend: <http://127.0.0.1:8000/health>

Both containers run as unprivileged users. The frontend image serves the SPA
through nginx with a history fallback, so deep links such as `/planner` resolve.

## Next real integrations

- Expand the crop dataset with independently validated regional samples.
- Add an OpenWeatherMap key and district-level rainfall history.
- Connect official Agmarknet/eNAM transactions to replace the planning baseline.
- Validate Gemini prompts and screening results with regional agriculture experts.
- Train a specialist disease model once a labelled dataset is available.

## Licence

MIT. See `LICENSE`.
