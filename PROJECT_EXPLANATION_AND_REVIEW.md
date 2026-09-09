# Annapurna AI: Project Explanation and Technical Review

Reviewed on: 9 September 2026  
Reviewed branch: `main` at commit `2156716`  
Repository: https://github.com/GurmeharSinghKalra/annapurna-ai

## 1. What Annapurna AI Is

Annapurna AI is a college-project prototype for crop recommendation and agricultural advisory. Its goal is to help a farmer enter farm conditions and receive a ranked crop plan with reasons, risks, estimated economics, soil guidance, weather context, crop rotation advice, and sustainability information.

The name comes from Annapurna, a Hindu goddess associated with nourishment and food. The application uses that theme as the identity of an agricultural decision-support product; it does not claim that mythology is part of the recommendation algorithm.

This is an **end-to-end prototype**, not a production agricultural advisory platform. It works offline in demo mode and labels unavailable external data sources instead of pretending they are live.

## 2. What a User Can Do

1. Open the landing page and create a farmer account.
2. Enter farm location, season, previous crop, soil type, land size, pH, NPK values, temperature, humidity, rainfall, budget, and decision priority.
3. View ranked crop matches in the crop planner.
4. Run complete analysis to call the backend and receive weather, soil health, market outlook, economics, crop rotation, sustainability, and an optional Gemini explanation.
5. Open Insights to see the supporting data for the selected plan.
6. Ask the AI advisor about irrigation, fertilizer, disease, or market planning.
7. Upload a leaf image for a preliminary crop-health screening.
8. Save a plan to SQLite history and export a plain-text report.
9. View system status for the model and external integrations.

## 3. Architecture

```text
Browser (React + Vite)
    |
    | HTTP requests to FastAPI
    v
FastAPI application
    |-- recommendation engine: transparent crop scoring
    |-- optional scikit-learn classifier: small ML influence
    |-- soil / weather / market adapters
    |-- Gemini service: explanation, chat, image screening
    |-- SQLite: users and saved recommendation history
    v
External services, only when API keys or official feeds are configured
    |-- OpenWeatherMap
    |-- Gemini
    |-- Agmarknet / eNAM
    |-- SoilGrids / ISRO Bhuvan integration boundary
```

The important design idea is that core recommendations are deterministic. Gemini is intended to explain a ranking or answer questions; it should not choose the crop itself. When credentials are absent, the application uses local fallbacks.

## 4. Frontend

Location: `src/`

The frontend is a React 19 single-page application built with Vite. `src/main.jsx` contains the routes, application state, UI components, local fallback behavior, and API calls. `src/styles.css` contains the responsive visual system.

Routes include:

| Route | Purpose |
| --- | --- |
| `/` | Public landing page |
| `/about` | Project and responsible-use overview |
| `/register`, `/login` | Farmer account screens |
| `/dashboard` | Farm overview and quick actions |
| `/planner` | Farm input form and crop comparison |
| `/insights` | Soil, weather, market, economics, rotation, sustainability |
| `/disease` | Leaf-image screening |
| `/advisor` | Context-aware farm chat |
| `/records` | Saved plans |
| `/settings` | Integration status and report export |

The frontend can calculate a browser-only recommendation when the API is offline. That is useful for a classroom demonstration, but it currently duplicates backend recommendation logic, which is one of the issues listed below.

## 5. Backend

Location: `backend/app/`

FastAPI exposes the REST API. The most important endpoint is `POST /analysis`, which receives a farm profile and returns:

- top crop recommendations;
- expected yield, cost, revenue, profit, margin, and sustainability score;
- weather source and readings;
- soil-health score and actions;
- market planning data for the top crops;
- a Gemini explanation if Gemini is configured;
- clear labels when a fallback was used.

Other important routes are:

| Route | Purpose |
| --- | --- |
| `GET /health` | Server, ML-model, and Gemini status |
| `POST /auth/register`, `POST /auth/login` | Account prototype |
| `POST /recommendations` | Ranked recommendations only |
| `POST /chat` | Gemini or local advisory answer |
| `POST /disease` | Image screening response |
| `GET/POST /history` | Saved recommendation history |
| `POST /reports/recommendation` | Downloadable text report |
| `GET /integrations/status` | Integration configuration status |
| `GET /admin/summary` | Basic application counts and status |

SQLite persists user records and recommendation history in `backend/data/annapurna_ai.sqlite`. The database file is intentionally ignored by Git.

## 6. Recommendation and AI Logic

### Transparent crop ranking

`backend/app/recommender.py` has a catalog of eight crops: Rice, Maize, Cotton, Wheat, Mustard, Chickpea, Sugarcane, and Pearl Millet. It scores each crop using:

- season match;
- soil type match;
- pH, temperature, and rainfall ranges;
- NPK nutrient condition;
- farmer priority: profit, sustainability, water saving, or balanced;
- previous-crop rotation;
- a small optional boost when the ML model predicts the same crop.

The result includes reasons and cautions so the score is explainable. It also produces planning yield, cost, revenue, expected profit, market trend, water need, rotation note, advisory, and sustainability score.

### Machine learning model

`backend/scripts/train_model.py` trains a scikit-learn `RandomForestClassifier` inside a pipeline with `DictVectorizer`. The data file is `backend/data/crop_training_sample.csv`.

The current starter dataset has only 24 rows. It exists to demonstrate the ML pipeline and generated `joblib` model, not to prove field-level accuracy. The ML model should not be presented as validated agricultural intelligence until it is trained and evaluated on a much larger, regional, independently checked dataset.

### Gemini features

When `GEMINI_API_KEY` is set in the backend environment, Gemini is used for:

- an explanation of the already-determined crop ranking;
- multilingual farmer chat;
- a structured visual crop-health screening from an uploaded image.

Without a key, the project responds with local advisory text and a clearly labelled placeholder screening result. Gemini screening is advisory only and must not be used as a disease diagnosis or pesticide recommendation.

## 7. External Data Status

| Source | Current main-branch behavior |
| --- | --- |
| OpenWeatherMap | Uses live temperature/humidity only when a key is set; otherwise uses farmer-entered values. |
| SoilGrids / ISRO Bhuvan | Adapter-ready labels only; no actual coordinate lookup exists yet. |
| Agmarknet / eNAM | Curated demo price/trend baselines; no live official transaction ingestion exists yet. |
| Gemini | Optional; fallback behavior works without a key. |

This labelling is a strength of the prototype: it makes the difference between a live feed and a planning baseline visible.

## 8. Verified Review Results

The following checks were run on the pulled `main` branch:

| Check | Result |
| --- | --- |
| `git pull --ff-only` | Pulled successfully to commit `2156716`. |
| `npm run build` | Passed. Vite built 1,573 modules. |
| `python scripts/train_model.py` | Passed; trained a model from 24 samples. |
| `python -m pytest` | Passed: 10 tests. |
| FastAPI `/health` | Passed; API running at `http://127.0.0.1:8000`. |
| FastAPI `POST /analysis` | Passed; returned crop ranking, weather, soil, markets, and local AI fallback. |
| FastAPI `POST /chat` | Passed with the labelled local advisory fallback. |
| FastAPI history save/list | Passed. |
| Browser landing page, registration, dashboard, and planner | Rendered and completed registration against the live backend. |
| Docker Compose validation | Not run because Docker is not installed on this computer. |

Running locally now:

- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`
- API reference: `http://127.0.0.1:8000/docs`

## 9. Problems Found on `main`

These findings are important before treating the project as production-ready.

### High priority: account and history data are not protected

The current login route verifies a password but returns only user data. It does not issue a session or access token. `GET /history`, `POST /history`, and `GET /admin/summary` have no authorization, so saved plans are not scoped to the logged-in farmer and any caller of the API can read or add history records. This is unsuitable for real farmer data.

### High priority: browser and server can disagree on the crop plan

`src/main.jsx` contains a separate local `scoreCrop` implementation. It differs from the backend because it does not include the ML model or previous-crop rotation. The dashboard can therefore display a browser-only ranking that is different from the result returned by `POST /analysis`. A production application should use one server-side source of truth and present an explicit offline state when the API is unavailable.

### High priority: economics are not consistently derived from yield and price

The current recommendation engine derives `expected_profit` from a manually entered `base_profit`, then sets revenue to cost plus profit. That may conflict with the displayed yield and market price. For example, displayed revenue should be reproducible as `expected yield x market price`; it currently is not guaranteed to be. The budget check also compares the budget with a profit-derived value rather than directly checking whether it covers estimated cultivation cost.

### High priority: disease fallback can falsely imply image analysis

The fallback accepts arbitrary bytes marked as `image/png` and returns `leaf stress detected` even when the file is not an image. The current automated test deliberately uses non-image bytes and expects success. The API should decode and validate the image before any response, and its fallback should say that visual analysis is unavailable rather than making a crop-health prediction.

### Medium priority: ML evidence is insufficient

The training data has 24 hand-curated rows, no tracked data provenance, no train/test evaluation report, and no confidence threshold that prevents an unreliable model from affecting the score. This is acceptable for a demo of ML integration, but not for a claim of recommendation accuracy.

### Medium priority: deployment is incomplete

The frontend defaults to `http://127.0.0.1:8000`. A frontend deployed to a public host would try to call the visitor's own computer unless `VITE_API_URL` is built with the real API URL. The current Docker frontend uses default nginx configuration, so refreshing a client-side route such as `/planner` is likely to produce a 404 instead of returning the SPA. Docker could not be verified locally because Docker Desktop is absent.

### Medium priority: operational safeguards are missing

There is no rate limiting for login, no password-reset flow, no admin authorization, no audit log, no database backup strategy, no CI workflow on `main`, and no frontend test suite. Passwords use PBKDF2, which is better than plaintext, but the current 100,000 iteration setting and no-session model need strengthening before real accounts are used.

### Low priority: status wording can confuse users

The UI displays `Advisory online` even when Gemini and external data are unconfigured and only local fallback behavior is in use. The status should tell the user whether the response is local, live, or unavailable.

## 10. Important GitHub Branch to Review Before Further Development

The repository already contains an unmerged branch:

```text
origin/audit/fix-security-correctness-and-deploy
```

It contains targeted fixes for most serious findings above, including token-based sessions, farmer-scoped history, login rate limiting, improved password hashing, corrected economics, server-only recommendation logic, upload validation, SPA nginx routing, Docker health checks, linting, CI, and a larger hermetic test suite.

It should be reviewed, tested, and merged through a pull request rather than copied blindly. The current review recommends treating that branch as the next development milestone.

## 11. How to Demonstrate This Project

For a classroom demo:

1. Open `http://127.0.0.1:5173`.
2. Register a demo farmer with a non-real phone number and password.
3. Open Crop Planner and explain the inputs: season, soil, pH, NPK, rainfall, budget, priority, and previous crop.
4. Change season or rainfall and show the crop ranking changes.
5. Click Run complete analysis and open Insights.
6. Explain that weather, market, and Gemini services currently use labelled fallbacks unless keys are configured.
7. Save a plan, show Saved Plans, and export the report.
8. Show `http://127.0.0.1:8000/docs` to demonstrate the backend API.
9. State the limitations honestly: the data is starter/demo data, disease analysis is screening only, and production needs validated regional datasets plus secure authentication.

## 12. Next Development Order

1. Review and merge the existing audit branch through a pull request.
2. Replace the 24-row starter dataset with validated regional data and publish evaluation metrics.
3. Add genuine OpenWeatherMap, SoilGrids/ISRO, and official Agmarknet/eNAM integrations with source timestamps.
4. Validate disease uploads and use a labelled specialist crop-disease model.
5. Deploy the frontend and backend with a real API URL, allowed CORS origins, HTTPS, secure secret storage, monitoring, and database backups.
6. Test with farmers and agriculture experts before making high-impact crop, cost, disease, or treatment claims.

## 13. Useful Project Files

| File | Why it matters |
| --- | --- |
| `src/main.jsx` | Frontend routes, state, local fallback, and API calls. |
| `backend/app/main.py` | FastAPI routes and complete analysis workflow. |
| `backend/app/recommender.py` | Crop scoring and planning values. |
| `backend/app/gemini_service.py` | Gemini explanation, chat, and screening boundary. |
| `backend/scripts/train_model.py` | ML model training script. |
| `backend/data/crop_training_sample.csv` | Starter ML data. |
| `docs/ARCHITECTURE.md` | Existing concise architecture guide. |
| `docs/DEFENSE_GUIDE.md` | Viva and presentation talking points. |
| `PROPOSAL_COVERAGE.md` | Mapping from proposal requirements to implementation. |

## Final Assessment

Annapurna AI is a credible, visually complete college-project prototype: it has a usable frontend, a functioning API, persistent data, transparent recommendation logic, an ML training example, optional Gemini workflows, and practical documentation. It should be presented as a **decision-support prototype with labelled demo fallbacks**, not as a validated live agricultural advisory service. The unmerged audit branch is the right next step because it addresses the gap between a working demo and a safer, more defensible system.
