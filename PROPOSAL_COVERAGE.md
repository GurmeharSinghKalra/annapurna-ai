# Proposal coverage

Each proposal requirement against what the code actually does, with the file to check.

| Requirement | Status | Where | Notes |
| --- | --- | --- | --- |
| Web interface | Done | `src/` | React 19 + Vite. Public pages, planner, insights, finance, crop health, advisor, saved plans, system. |
| Mobile-friendly | Done | `src/styles.css`, `public/manifest.webmanifest` | Responsive layout, PWA manifest and service worker, all present in the Docker image. |
| User accounts | Done | `backend/app/routers/auth.py` | Phone + password, argon2, rotating refresh tokens with theft detection, account deletion. **Optional** — every planning route works signed out. |
| Crop recommendation engine | Done | `backend/app/recommender.py` | Weighted score plus hard limiters, so the product can say "not recommended" and name the reason. |
| Soil, weather, crop input capture | Done | `src/workspace.jsx`, `backend/app/schemas.py` | Validated per field, with ranges and units stated. Irrigation access added, because ranking a thirsty crop without it is meaningless. |
| Yield, profit, sustainability outputs | Done | `backend/app/recommender.py`, `crop_data.py` | Reported as poor/typical/good ranges with cited sources, not single figures. Sustainability responds to the field, not only the crop. |
| Crop rotation | Done | `backend/app/crop_data.py` | Beneficial rotations score up, repeating last season's crop scores down with an explicit caution. |
| Integrated workflow | Done | `POST /analysis` | Weather, soil, ranking, rotation, market and the AI explanation from one profile. |
| Weather integration | Done | `backend/app/weather.py` | OpenWeatherMap with geocoding, a five-day rain outlook and caching. Without a key the screen says the values are the farmer's own, rather than showing them as a reading. |
| Soil data integration | Partial | `backend/app/integrations.py` | pH and NPK are farmer-entered and interpreted against soil-health-card bands. **No soil laboratory or satellite feed is connected**, and the API reports `not_implemented` rather than "adapter_ready". |
| Market data integration | Done | `backend/app/market_data.py` | AGMARKNET daily mandi prices via data.gov.in, using the dataset's own commodity names, cached per district, newest-record selection, with trend measured from stored history. **Works with no key at all** via a keyless mirror covering 5 states; falls back to labelled MSP beyond that. |
| Multilingual chatbot | Done | `backend/app/gemini_service.py`, `advisory.py` | Gemini in English, Hindi, Punjabi and Haryanvi. The offline template is fully translated and states that it is not an answer. |
| Crop disease detection | Partial | `POST /disease` | Gemini multimodal screening with validation and size limits. **No specialist disease model**, so without a key it returns 503 rather than a fabricated diagnosis. |
| Farmer history | Done | `backend/app/routers/records.py` | Saved plans, season budgets and named farm profiles stored server-side per account, with pagination and reopen. Guests keep plans in the browser, and the UI says so. |
| Reports | Done | `backend/app/reports.py` | Text and PDF. Both carry ranges, the verdict, any limiter, the price basis and the sources. The server recomputes the recommendation, so a client cannot forge a branded report. |
| Admin / status view | Done | `/health`, `/readyz`, `/integrations/status`, `/admin/summary` | Reports what is genuinely connected, plus the crop model's measured accuracy. |
| Docker / cloud readiness | Done | `docker-compose.yml`, both Dockerfiles | PostgreSQL, migrations on boot, healthchecks, non-root users, request-time DNS resolution in nginx. |
| Ethics and compliance | Done | Throughout | Every figure states its basis; unconnected services say so; no bank, credit or payment data is collected anywhere. |

## Production boundary

These need credentials, datasets or partners, and are not pretended to exist:

- **District-level cost and yield datasets.** The table is one regional range per crop.
- **A labelled disease dataset and specialist classifier.** Today it is general-purpose vision.
- **Soil laboratory or satellite integration.** Today soil is farmer-entered.
- **Agronomist review** of the reference table, recorded per crop with a date.
- **Shared rate limiting** for more than one API replica.
- **Email or SMS delivery**, without which there is no password reset.

## Verify

```bash
cd backend
ruff check app scripts tests && ruff format --check app scripts tests
python scripts/build_dataset.py && python scripts/train_model.py
python -m pytest                                    # 169 tests
alembic upgrade head && alembic downgrade base && alembic upgrade head

cd ..
npm run lint && npm test -- --run && npm run build  # 38 tests
docker compose config
```
