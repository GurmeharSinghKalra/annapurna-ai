# Annapurna AI Proposal Coverage

This document maps the project proposal to the current implementation.

## Implemented

| Proposal item | Current implementation |
| --- | --- |
| User-friendly web interface | React/Vite workspace in `src/main.jsx` with responsive CSS in `src/styles.css`. |
| Mobile-friendly experience | PWA manifest, icon, runtime-caching service worker, and responsive layout. The Docker image ships all of them and serves client-side routes through an nginx history fallback. |
| User authentication and management | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`. Opaque bearer tokens stored hashed with expiry; PBKDF2-SHA256 at 600k iterations; failed sign-ins throttled. Protected routes are enforced on both the server and the client. |
| Crop recommendation engine | `backend/app/recommender.py`, plus an optional scikit-learn model whose influence is gated on its measured cross-validated accuracy. |
| Soil, weather, and crop input capture | Frontend farm form; `FarmProfile` schema with every agronomic field required and range-checked. |
| Yield/profit/sustainability outputs | Recommendation cards and `/analysis` return yield, cost, revenue, profit, margin, water demand, budget coverage, and a sustainability score. Revenue is always yield x price and profit is always revenue minus cost. |
| Crop rotation recommendation | The planner captures the previous crop; beneficial rotations receive a ranking boost surfaced as the leading reason, and repeating a crop receives an explicit caution and score penalty. |
| Integrated decision workflow | `/analysis` runs weather, soil health, ranked recommendations, rotation, market outlook, economics, sustainability, and the Gemini explanation from one farm profile, and reports the provenance of each input it used. |
| Weather integration | `/weather` and `/analysis` use OpenWeatherMap when configured and clearly labelled manual values otherwise. Upstream failures degrade to the fallback instead of erroring. |
| Soil data integration | `/soil` and `/analysis` calculate a soil-health score and actionable pH/NPK guidance, with SoilGrids/ISRO-ready source labelling. |
| Market data integration | `/market` and `/analysis` expose commodity names, planning prices, trends, and adapter status for Agmarknet/eNAM. |
| Multilingual chatbot | Gemini-backed `/chat` with English, Hindi, Punjabi, and Haryanvi fallbacks. Farmer text is fenced in the prompt and marked untrusted. |
| Crop disease detection module | Frontend upload and `/disease`, validating image type from the file's own bytes and capping upload size. Without Gemini it reports that no screening ran rather than inventing a prediction. |
| Farmer history | SQLite-backed `/history`, scoped to the authenticated account. |
| Reports | `/reports/recommendation`, used by the frontend export so the report and the screen cannot disagree. |
| Admin/status view | `/admin/summary` behind an admin token, plus public `/crops` and `/integrations/status`. |
| Docker/cloud readiness | `Dockerfile.frontend`, `backend/Dockerfile`, and `docker-compose.yml`. Both containers run unprivileged, both have healthchecks, and the frontend waits for backend health. |
| Ethics and compliance visibility | Frontend safeguards panel, `.env.example` for key separation, and labelled `source`/`live` fields on every data response. |

## Production data boundary

These require credentials, official feeds, or labelled datasets, and are
intentionally outside the prototype:

- Live OpenWeatherMap key in `OPENWEATHER_API_KEY`.
- Official Agmarknet/eNAM source URLs for current mandi transactions.
- Gemini API key for explanations, advisory, and multimodal screening.
- A labelled crop-disease image dataset and trained classifier.
- A larger validated regional crop dataset.

## Known limitations

Stated plainly, because the point of the project is that advice should not hide
uncertainty:

- **The starter ML dataset is not usable for real decisions.** 24 rows, 2–4 per
  class, cross-validated accuracy around 0.63. Training reports that number and the
  API scales the model's influence by it. The deterministic rules carry the ranking.
- **Market prices are a planning baseline, not live quotes.** Every response says
  so, and the UI repeats it.
- **Crop cost, yield, and price figures are planning estimates** that have not been
  validated against regional survey data.
- **Rate limiting is per process.** A multi-worker deployment needs a shared limiter.
- **SQLite suits a prototype**, not concurrent production traffic.
- **Disease screening is advisory.** It is a general multimodal model, not a trained
  crop pathologist, and expert confirmation matters before treatment.

## Verification

```bash
npm run lint && npm run build
```

```bash
cd backend && python scripts/train_model.py && python -m pytest -q
```

```bash
docker compose build && docker compose up -d --wait
```

Current status: lint passes, frontend build passes, model training passes,
96 backend tests pass, both images build, and the running stack serves deep links
and PWA assets. CI enforces all of it.
