# Architecture

Annapurna AI is split into a React frontend and a FastAPI backend.

## Frontend

- Location: `src/`
- Framework: React with Vite
- Main entry: `src/main.jsx`
- Styling: `src/styles.css`
- PWA assets: `public/manifest.webmanifest`, `public/icon.svg`, `public/sw.js`. The service worker
  caches same-origin app assets only after a successful visit; API responses are never cached.

The frontend provides:

- Farmer profile form
- Crop recommendation cards
- Yield/profit/sustainability insights
- Weather panel
- Gemini multimodal disease-screening panel
- Gemini multilingual advisor panel
- Device-local saved-plans panel
- Data-source status panel
- System-status panel
- Text report export

## Backend

- Location: `backend/app/`
- Framework: FastAPI
- Main entry: `backend/app/main.py`
- ML model: scikit-learn pipeline trained by `backend/scripts/train_model.py`

Backend modules:

- `schemas.py`: request/response models
- `database.py`: legacy prototype persistence; the active API has no account or shared-history route
- `recommender.py`: crop catalog and recommendation scoring
- `ml_model.py`: model loading and prediction
- `integrations.py`: weather, soil, market, and integration-status adapters
- `advisory.py`: multilingual advisory responses
- `reports.py`: text recommendation report generation

## Data Flow

1. User enters farm details in the frontend.
2. Frontend can calculate local fallback recommendations immediately.
3. Clicking Run complete analysis sends the farm profile and previous crop to `POST /analysis`.
4. Backend labels and combines weather, soil health, market context, rotation-aware ranking, economics, and sustainability metrics.
5. The trained model augments transparent local scoring; Gemini explains the ranking without changing it.
6. User can save plans on the current device, ask Gemini questions, upload a disease image for Gemini screening, and export a report.

## Storage

The active tool uses browser storage for device-local saved plans and finance inputs. The legacy
SQLite module is not imported by the active API and exists only to preserve old local prototype
databases; it is ignored by Git.
