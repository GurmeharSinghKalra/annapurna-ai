# Architecture

Annapurna AI is split into a React frontend and a FastAPI backend.

## Frontend

- Location: `src/`
- Framework: React with Vite
- Main entry: `src/main.jsx`
- Styling: `src/styles.css`
- PWA assets: `public/manifest.webmanifest`, `public/icon.svg`, `public/sw.js`

The frontend provides:

- Farmer profile form
- Crop recommendation cards
- Yield/profit/sustainability insights
- Weather panel
- Gemini multimodal disease-screening panel
- Gemini multilingual advisor panel
- History panel
- Data-source status panel
- Admin console
- Text report export

## Backend

- Location: `backend/app/`
- Framework: FastAPI
- Main entry: `backend/app/main.py`
- Data storage: SQLite
- ML model: scikit-learn pipeline trained by `backend/scripts/train_model.py`

Backend modules:

- `schemas.py`: request/response models
- `database.py`: SQLite setup, users, and history persistence
- `recommender.py`: crop catalog and recommendation scoring
- `ml_model.py`: model loading and prediction
- `integrations.py`: weather, soil, market, and integration-status adapters
- `advisory.py`: multilingual advisory responses
- `reports.py`: text recommendation report generation

## Data Flow

1. User enters farm details in the frontend.
2. Frontend can calculate local fallback recommendations immediately.
3. Clicking Sync API sends the farm profile to `POST /recommendations`.
4. Backend combines rule scoring with the trained scikit-learn model when available.
5. Gemini explains the ranked recommendation without changing the deterministic ranking.
6. User can save history, ask Gemini questions, upload a disease image for Gemini screening, and export a report.

## Storage

SQLite is used for prototype persistence:

- `users` table for farmer accounts
- `recommendation_history` table for saved plans

The generated SQLite database is ignored from Git.
