# Roadmap

## Phase 1: Prototype

Completed:

- Farm input form
- Crop recommendations
- Rule-based and ML-assisted scoring
- Device-local recommendation history
- Report export
- Gemini advisor with local fallback
- Gemini multimodal disease screening with local fallback
- System-status panel
- PWA and Docker setup

## Phase 2: Data Quality

- Add larger crop recommendation dataset.
- Validate crop ranges with agriculture sources.
- Add regional crop calendars.
- Add district-level soil and rainfall profiles.

## Phase 3: Live Integrations

- Connect OpenWeatherMap.
- Connect Agmarknet/eNAM or curated price feeds.
- Connect SoilGrids/ISRO Bhuvan data lookup.
- Evaluate Gemini responses with agriculture experts and multilingual farmer testing.

## Phase 4: Disease Detection

- Collect labelled crop disease images.
- Train image classifier.
- Add confidence thresholds.
- Add expert-confirmation warnings.

## Phase 5: Deployment

- Deploy backend to cloud.
- Deploy frontend to static hosting.
- Decide whether a future multi-device product needs scoped identity and encrypted persistence.
- Add analytics and monitoring.
