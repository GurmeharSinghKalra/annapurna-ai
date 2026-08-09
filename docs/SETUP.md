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
- `AGMARKNET_SOURCE_URL`
- `ENAM_SOURCE_URL`

Gemini is used by recommendation explanations, the multilingual farm advisor, and
multimodal crop-image screening. Leave the key empty to use deterministic local fallbacks.

The app works without these values using local fallback behavior.

## Docker

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
