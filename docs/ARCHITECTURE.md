# Architecture

Annapurna AI is a React frontend and a FastAPI backend. The backend owns every
agronomic decision; the frontend renders them.

## Why ranking lives only on the server

An earlier version scored crops in both places. The two implementations drifted:
the browser copy ignored crop rotation, so with a previous crop of wheat the server
recommended mustard while an offline client recommended planting wheat again — the
exact thing the server penalised for pest and nutrient pressure.

There is now one implementation, in `backend/app/recommender.py`. When the API is
unreachable the client replays the last analysis the server actually returned,
labelled with its age, and offers to re-run. It never generates fresh advice
locally. Stale real advice is recoverable; confidently wrong advice is not.

## Frontend

- Location: `src/`
- Framework: React 19 with Vite 7 (`vite.config.js`, React Fast Refresh enabled)
- Entry: `src/main.jsx` · API client: `src/api.js` · Styling: `src/styles.css`
- PWA assets: `public/manifest.webmanifest`, `public/icon.svg`, `public/sw.js`

`src/api.js` owns the network boundary: bearer tokens, error normalisation, the
`ApiError` type, session storage, and the cached-analysis store. A `401` from any
call clears the session and returns the user to sign-in.

Routes `/dashboard`, `/planner`, `/insights`, `/disease`, `/advisor`, `/records`,
and `/settings` require an account. `/`, `/about`, `/login`, and `/register` are public.

The service worker caches same-origin responses as they are fetched, so a second
visit works offline. It never answers a missing asset with the app shell — that
makes the browser refuse the response and renders a blank page.

## Backend

- Location: `backend/app/`, entry `backend/app/main.py`
- Storage: SQLite (`users`, `sessions`, `recommendation_history`)
- Model: scikit-learn pipeline trained by `backend/scripts/train_model.py`

| Module | Role |
| --- | --- |
| `main.py` | Routes, auth dependencies, lifespan, CORS |
| `schemas.py` | Request and response contracts, input validation |
| `security.py` | Password hashing, session tokens, login throttling |
| `database.py` | Connections, migrations, users, sessions, history |
| `recommender.py` | Crop scoring, rotation, economics, sustainability |
| `ml_model.py` | Cached model loading and accuracy-gated prediction |
| `integrations.py` | Weather, soil, market adapters with labelled fallbacks |
| `gemini_service.py` | Gemini boundary, prompt hardening |
| `advisory.py` | Offline multilingual advisory text |
| `reports.py` | Plain-text report generation |
| `uploads.py` | Image sniffing and upload size limits |
| `config.py` | Environment-driven settings |

Schema creation runs in the FastAPI lifespan, not at import. Settings are read once
per process through `get_settings()`, and the Gemini client is built on first use,
so configuration does not have to exist before the module is imported.

## Data flow

1. The farmer fills in the profile; `toApiFarm` converts it to the API contract.
2. **Run complete analysis** posts to `POST /analysis`.
3. The backend fetches weather (or labels the fallback), scores soil health, ranks
   crops with rotation context, derives economics, builds market outlooks, and asks
   Gemini to explain — never to reorder — the ranking.
4. The response is rendered and cached in the browser.
5. Insights, the advisor, disease screening, and reports all read that same
   analysis, so every screen describes one decision.

## Scoring

Agronomic fit (season, soil, pH, temperature, rainfall, nutrients) carries 78 of the
107 available points. Market priority, rotation, and the trained model are bounded
bonuses on top. The final score is normalised against the maximum rather than
clipped at a ceiling — clipping used to pin 16% of profiles to the same top value
and flatten the ranking. Out-of-range penalties scale with distance relative to the
width of the crop's tolerance band.

The trained model contributes at most 14 points, multiplied by both its prediction
confidence and its measured cross-validated accuracy. Below 60% accuracy it
contributes nothing, and `/admin/summary` says so.

## Storage

SQLite is prototype persistence. `users` holds accounts with PBKDF2-SHA256 hashes at
600,000 iterations; legacy hashes are upgraded on next successful sign-in.
`sessions` holds hashed opaque tokens with expiry. `recommendation_history` is keyed
by `user_id`. The database file is ignored by Git.
