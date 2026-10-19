# Annapurna AI

A crop planning and agricultural advisory application for Indian smallholders. It ranks crops
against a farmer's actual field conditions, builds a season budget with a downside case, and
carries the same context into image-based crop screening and a multilingual advisor.

The design rule throughout: **every number says where it came from, and the app says "I don't
know" rather than filling a gap.** When a data source is not connected, the screen reports that
instead of showing the farmer's own input back as if it were a measurement.

---

## What it does

**Crop ranking that can say no.** Season, soil, pH, temperature and water availability are hard
constraints, not soft weights. A crop that does not fit is labelled `not recommended` and the
disqualifying condition is named. Suitability is a real 0-100 score with no artificial floor.

**Economics as ranges.** Yield and cost vary with variety, irrigation and pest year, so every crop
reports a poor / typical / good case rather than one number that reads as a promise. Reference
prices are announced support prices (MSP) and are labelled as such; a live mandi price replaces
them when the market feed is connected.

**Season finance.** Category budget, tracked actual spend, cash-flow timing, break-even price and
break-even yield, peak working capital, and four scenarios built from the crop's real ranges.
No lending, credit scoring, or bank data — the product does not ask for any of it.

**Accounts, optionally.** Everything in the planner works signed out. An account stores saved
plans, season budgets and farm profiles server-side so they survive a cleared browser and reach a
second device.

**Advisory and screening.** A Gemini-backed advisor that answers in English, Hindi, Punjabi or
Haryanvi using the current field context, and crop-image screening that returns a cautious,
clearly-labelled result — or refuses, rather than guessing, when no vision model is configured.

---

## Quick start

```bash
git clone https://github.com/GurmeharSinghKalra/annapurna-ai.git
cd annapurna-ai
cp .env.example .env          # optional: everything runs without keys
```

**Backend** (Python 3.13):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python scripts/build_dataset.py && python scripts/train_model.py   # optional crop model
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 20+), in a second terminal:

```bash
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The dev server proxies `/api` to the backend, so the browser never
makes a cross-origin call and dev matches production.

**Docker**, for the whole stack including PostgreSQL:

```bash
cp .env.example .env
docker compose up --build
```

Frontend on <http://127.0.0.1:5174>, API on <http://127.0.0.1:8000>.

---

## API keys

Every key is optional. Without one, the dependent feature degrades to a clearly-labelled state
rather than a fake one.

| Key | Where to get it | With it | Without it |
| --- | --- | --- | --- |
| `AGMARKNET_API_KEY` | [data.gov.in](https://data.gov.in) — free | Every state, district-level daily modal prices, a measured trend, and a quota of your own | A keyless community mirror of the same government dataset covers 5 states out of the box (see below); elsewhere, labelled MSP |
| `OPENWEATHER_API_KEY` | [openweathermap.org](https://openweathermap.org/api) — free tier | Live temperature, humidity and a five-day rain outlook | Weather screens show the farmer's entered values, explicitly labelled as their own input |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/apikey) — free tier | Recommendation explanations, advisory chat, crop-image screening | Advisor uses a fixed template that states it is not an answer; image screening returns 503 rather than inventing a diagnosis |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` | Required for accounts in production | Development uses a shared placeholder and logs a warning; `APP_ENV=production` refuses to start |

Keys live in the backend environment only and are never exposed to the browser.

### Mandi prices work without any key

With no `AGMARKNET_API_KEY`, prices fall back to a keyless community mirror of the same
government dataset, so a fresh clone shows **real mandi prices immediately**:

```
/analysis  ·  Nagpur, Maharashtra  ·  no API keys configured

  LIVE  Cotton    92%  strong match        INR 8800/q   <- APMC Kinwat, Nanded, 2026-10-16
  LIVE  Rice      62%  workable with care  INR 3875/q
  LIVE  Maize     57%  workable with care  INR 2600/q
  MSP   Sugarcane 71%  good match          INR  360/q   <- no live price, labelled as MSP
```

The mirror covers Karnataka, Madhya Pradesh, Maharashtra, Punjab and Uttar Pradesh only, is
state-level rather than district-level, and shares one rate limit across all its users. Anything
it cannot answer falls back to a clearly-labelled support price rather than a guess. Get the free
official key for full coverage, including Haryana.

---

## Project layout

```
src/                      React frontend
  api.js                  HTTP client, typed errors, token refresh, guarded storage
  auth.jsx                account context
  planner-state.jsx       farm profile, analysis and finance state
  farm.js                 farm model, validation, API conversion
  components.jsx          shared UI primitives
  marketing.jsx           public landing and about pages
  account.jsx             sign in and registration
  workspace.jsx           the application screens
  *.test.jsx              frontend tests

backend/app/
  main.py                 routes, middleware, body limits, observability
  crop_data.py            agronomic reference data, with sources and ranges
  recommender.py          the ranking: weighted score plus hard limiters
  finance.py              season budget, cash flow, scenarios
  market_data.py          AGMARKNET prices, caching, measured trend
  weather.py              OpenWeatherMap, geocoding, forecast
  gemini_service.py       AI calls, prompt-injection fencing, model fallback
  reports.py              text and PDF reports
  models.py / db.py       SQLAlchemy models and engine
  security.py / deps.py   hashing, tokens, rate limiting
  routers/                accounts and records
backend/migrations/       Alembic migrations
backend/tests/            137 backend tests
distribution/             Windows portable build
```

---

## Documentation

- [`docs/SETUP.md`](docs/SETUP.md) — local, Docker and production setup
- [`docs/API.md`](docs/API.md) — every route, with request and response shapes
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the pieces fit, and why
- [`docs/DATA.md`](docs/DATA.md) — where every agronomic and price figure comes from
- [`docs/TESTING.md`](docs/TESTING.md) — running and extending the suites
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — what is deliberately not built yet
- [`PROPOSAL_COVERAGE.md`](PROPOSAL_COVERAGE.md) — proposal requirements against the implementation

---

## Verify

```bash
# Backend
cd backend
ruff check app scripts tests && ruff format --check app scripts tests
python -m pytest
alembic upgrade head && alembic downgrade base && alembic upgrade head

# Frontend
npm run lint
npm test -- --run
npm run build
```

CI runs all of the above plus migrations against PostgreSQL and both Docker image builds.

---

## Limits worth stating plainly

- Reference agronomic data covers the **irrigated North-Indian plains** (Haryana, Punjab, western
  Uttar Pradesh). Elsewhere it needs revalidation before it should be trusted.
- Support prices are **not** sale prices. Yield and cost ranges are regional planning figures, not
  a forecast for any particular field.
- Image screening is a screening aid. It is never a diagnosis.
- The optional crop model is trained on rows derived from the documented agronomic envelopes, not
  on observed field records. Its influence on the ranking is scaled by its measured accuracy
  against a held-out observational sample, and `/admin/summary` reports those numbers.
- Rate limiting is in-process, so it is correct for a single API replica only. `/health` says so.
