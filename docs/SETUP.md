# Setup Guide

## Requirements

- Node.js 22 or newer
- Python 3.13 or newer
- Git
- Optional: Docker Desktop

## Frontend

```powershell
cd "C:\Users\ameri\Documents\New project\annapurna-ai"
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Backend

```powershell
cd "C:\Users\ameri\Documents\New project\annapurna-ai\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\train_model.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/health
```

## Environment Variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Supported keys:

- `OPENWEATHER_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (defaults to `gemini-3.6-flash`)
- `GEMINI_TIMEOUT_SECONDS` (defaults to 20; a timeout uses the local advisory fallback)
- `AGMARKNET_SOURCE_URL`
- `ENAM_SOURCE_URL`
- `CORS_ORIGINS` (comma-separated allowed frontend origins; defaults to local development URLs)

Gemini is used by recommendation explanations, the multilingual farm advisor, and
multimodal crop-image screening. Leave the key empty to use deterministic local fallbacks.

The app works without these values using local fallback behavior.

### Optional market-feed contract

`AGMARKNET_SOURCE_URL` and `ENAM_SOURCE_URL` are optional backend URLs, not browser URLs. If either
is set, Annapurna requests it with `commodity`, `location`, and `format=json` query parameters.
The endpoint must return JSON containing a list under `data`, `records`, `results`, or `items` (or
a single object). Each matching record must contain `commodity` or `crop`, plus
`modal_price_per_quintal` or `modal_price`, expressed in INR per quintal. A compatible result is
labelled as a live feed; an unavailable or incompatible result automatically retains the curated
planning baseline. Do not configure a feed unless its source and unit are verified.

## Docker

In Docker, the browser calls the frontend at port 5174 and Nginx forwards `/api/*` to the backend
container. The production frontend therefore does not depend on `127.0.0.1:8000` being available
on the farmer's device.

The Nginx configuration also applies basic browser-security headers and prevents long-lived service
worker caching, so a new frontend deployment can replace an older offline shell.

```powershell
docker compose up --build
```

Frontend:

```text
http://127.0.0.1:5174
```

Backend:

```text
http://127.0.0.1:8000/health
```
