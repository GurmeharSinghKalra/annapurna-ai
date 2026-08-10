# Setup Guide

## Requirements

- Node.js 22 or newer
- Python 3.13 or newer
- Git
- Optional: Docker Desktop

Commands below are POSIX shell (macOS and Linux). On Windows PowerShell only the
virtualenv activation differs; each such step notes the alternative.

## Frontend

From the repository root:

```bash
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

## Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
```

PowerShell: replace the activation line with `.\.venv\Scripts\Activate.ps1`.

`requirements-dev.txt` pulls in `requirements.txt` and adds the test tooling.
Production images install `requirements.txt` only.

```bash
python scripts/train_model.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/health>. Interactive API docs are at `/docs`.

## Environment variables

```bash
cp .env.example .env
```

PowerShell: `Copy-Item .env.example .env`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENWEATHER_API_KEY` | Live weather | unset — farmer readings, labelled |
| `GEMINI_API_KEY` | Explanations, chat, image screening | unset — local fallbacks |
| `GEMINI_MODEL` | Model id | `gemini-3.6-flash` |
| `AGMARKNET_SOURCE_URL` | Official market feed | unset — curated baseline |
| `ENAM_SOURCE_URL` | Official market feed | unset — curated baseline |
| `ADMIN_TOKEN` | Enables `/admin/summary` | unset — endpoint returns 503 |
| `CORS_ORIGINS` | Comma-separated browser origins | localhost 5173 and 5174 |
| `VITE_API_URL` | API base compiled into the bundle | `http://127.0.0.1:8000` |
| `ANNAPURNA_DB_PATH` | SQLite location | `backend/data/annapurna_ai.sqlite` |
| `ANNAPURNA_MODEL_DIR` | Model artifacts | `backend/models` |
| `SESSION_TTL_HOURS` | Session lifetime | `336` (14 days) |
| `MAX_UPLOAD_BYTES` | Disease image cap | `8388608` (8 MB) |
| `LOGIN_ATTEMPT_LIMIT` | Failures before throttling | `10` |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | Throttle window | `300` |

The app works without any of the optional keys.

### Deploying somewhere other than localhost

Two values must change together, or the browser will be blocked by CORS:

1. `VITE_API_URL` — the public URL of the API, set **before** the frontend build.
2. `CORS_ORIGINS` — the public origin of the frontend, set on the backend.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Frontend: <http://127.0.0.1:5174> · Backend: <http://127.0.0.1:8000/health>

The frontend waits for the backend's healthcheck before starting. To point the
built bundle at a different API:

```bash
VITE_API_URL=https://api.example.com docker compose build frontend
```

## Admin endpoints

`/admin/summary` is disabled until `ADMIN_TOKEN` is set, and then requires the
token as a header:

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" http://127.0.0.1:8000/admin/summary
```
