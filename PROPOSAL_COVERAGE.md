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
| Yield/profit/sustainability outputs | Recommendation cards and `/analysis` return estimated cost, revenue, profit, margin, yield, water demand, and a numeric sustainability score. |
| Crop rotation recommendation | The planner captures the previous crop; beneficial rotations receive a ranking boost and repeated crops receive an explicit caution. |
| Integrated decision workflow | `/analysis` runs weather, soil health, ranked recommendations, rotation, market outlook, economics, sustainability, and Gemini explanation from one farm profile. |
| Weather integration | `/weather` and `/analysis` use OpenWeatherMap when configured and clearly labelled manual values otherwise. |
| Soil data integration | `/soil` and `/analysis` calculate a soil-health score and actionable pH/NPK guidance, with SoilGrids/ISRO-ready source labelling. |
| Market data integration | `/market` and `/analysis` expose commodity names, planning prices, trends, and official-feed adapter status for Agmarknet/eNAM. |
| Multilingual chatbot | Gemini-backed `/chat` with correctly encoded English, Hindi, Punjabi, and Haryanvi fallbacks. |
| Crop disease detection module | Frontend image upload and backend `/disease` route with prototype screening response. |
| Farmer history | SQLite-backed `/history` endpoints and frontend saved history panel. |
| Reports | Frontend text report export and backend `/reports/recommendation`. |
| Admin/status view | Frontend admin panel plus `/admin/summary`, `/crops`, and `/integrations/status`. |
| Docker/cloud readiness | `Dockerfile.frontend`, `backend/Dockerfile`, and `docker-compose.yml`. |
| Ethics and compliance visibility | Frontend Security and Ethics panel and `.env.example` for API-key separation. |

## Production Data Boundary

These are intentionally separated from the prototype because they require credentials, official feeds, or labelled datasets:

- Live OpenWeatherMap key in `OPENWEATHER_API_KEY`.
- Official Agmarknet/eNAM source URLs for current mandi transactions; the working app labels its built-in planning baseline.
- Gemini API key for crop explanations, multilingual advisory, and multimodal disease screening; safe local fallbacks remain available.
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
