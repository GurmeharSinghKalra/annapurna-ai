# Roadmap

## Phase 1: Prototype — complete

- Farm input form with validated, required agronomic inputs
- Server-side crop ranking with rotation and reconciling economics
- Token-based accounts with per-farmer data isolation
- Recommendation history and text report export
- Gemini advisor and multimodal disease screening, each with a labelled fallback
- Accuracy-gated ML pipeline
- Admin/status endpoints behind an admin token
- PWA, Docker Compose, and CI

## Phase 2: Data quality

- Replace the 24-row starter dataset with validated regional samples.
- Validate crop tolerance ranges against agricultural extension sources.
- Validate cost, yield, and price baselines against regional survey data.
- Add regional crop calendars and district-level soil and rainfall profiles.

## Phase 3: Live integrations

- Connect OpenWeatherMap, including a real seasonal rainfall source rather than
  the farmer's estimate.
- Connect Agmarknet/eNAM or a curated price feed.
- Connect SoilGrids/ISRO Bhuvan lookup by coordinates.
- Evaluate Gemini responses with agriculture experts and multilingual farmer testing.

## Phase 4: Disease detection

- Collect a labelled crop-disease image dataset.
- Train an image classifier and report its held-out accuracy.
- Add confidence thresholds and expert-confirmation warnings.

## Phase 5: Production hardening

- Move from SQLite to a managed database; add backups and migrations.
- Replace the in-process rate limiter with a shared one for multi-worker deployments.
- Add refresh-token rotation and account recovery.
- Add structured logging, metrics, tracing, and error reporting.
- Deploy the backend to a managed host and the frontend to static hosting.
