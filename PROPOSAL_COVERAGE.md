# Annapurna AI Proposal Coverage

This document maps the project proposal to the current implementation.

## Implemented

| Proposal item | Current implementation |
| --- | --- |
| User-friendly web interface | React/Vite dashboard in `src/main.jsx` with responsive CSS in `src/styles.css`. |
| Mobile-friendly experience | PWA manifest, icon, service worker, and responsive mobile layout. |
| User authentication and management | FastAPI `/auth/register` and `/auth/login`; SQLite `users` table with password hashing. |
| Crop recommendation engine | `backend/app/recommender.py` plus trainable scikit-learn model in `backend/scripts/train_model.py`. |
| Soil, weather, and crop input capture | Frontend farm profile form; backend `FarmProfile` schema. |
| Yield/profit/sustainability outputs | Recommendation cards, advisory panels, `/recommendations`, and report export. |
| Crop rotation recommendation | Stored in crop catalog and shown in advisory/report output. |
| Weather integration | `/weather` endpoint with OpenWeatherMap adapter and manual fallback. |
| Soil data integration | `/soil` endpoint with SoilGrids/ISRO Bhuvan adapter placeholder and manual profile fallback. |
| Market data integration | `/market` endpoint with Agmarknet/eNAM adapter status and demo price-band fallback. |
| Multilingual chatbot | `/chat` endpoint with English, Hindi, Punjabi, and Haryanvi fallback responses. |
| Crop disease detection module | Frontend image upload and backend `/disease` route with prototype screening response. |
| Farmer history | SQLite-backed `/history` endpoints and frontend saved history panel. |
| Reports | Frontend text report export and backend `/reports/recommendation`. |
| Admin/status view | Frontend admin panel plus `/admin/summary`, `/crops`, and `/integrations/status`. |
| Docker/cloud readiness | `Dockerfile.frontend`, `backend/Dockerfile`, and `docker-compose.yml`. |
| Ethics and compliance visibility | Frontend Security and Ethics panel and `.env.example` for API-key separation. |

## Needs Real External Inputs Before Production

These are intentionally separated from the prototype because they require credentials, official feeds, or labelled datasets:

- Live OpenWeatherMap key in `OPENWEATHER_API_KEY`.
- Official Agmarknet/eNAM source URLs or curated market dataset.
- Gemini API key for crop explanations, multilingual advisory, and multimodal disease screening.
- Labelled crop disease image dataset and trained classifier.
- Larger validated regional crop dataset for robust ML accuracy.

## Verification Commands

```powershell
npm run build
cd backend
.\.venv\Scripts\python.exe scripts\train_model.py
.\.venv\Scripts\python.exe -m pytest
docker compose config
```

Current verification status: frontend build passes, model training passes, backend tests pass, and Docker Compose config is valid.
