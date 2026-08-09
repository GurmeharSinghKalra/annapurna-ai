# Defense Guide

## One-Line Project Explanation

Annapurna AI is an AI-based crop recommendation and agricultural advisory system that helps farmers choose suitable crops using soil, weather, nutrient, market, and sustainability factors.

## Problem Statement

Farmers often lack localized, data-driven guidance for crop selection. Generic advisory systems do not consider soil nutrients, weather, rainfall, crop rotation, market priority, or language accessibility together.

## What To Demonstrate

1. Open the dashboard.
2. Change farm conditions.
3. Show crop recommendations changing.
4. Explain suitability score, reasons, and warnings.
5. Show yield/profit/sustainability panels.
6. Use Sync API.
7. Register/login a farmer.
8. Save a plan and show history.
9. Export a report.
10. Show the Gemini advisor and Gemini multimodal disease-screening flow.
11. Open Admin section and explain integrations.

## Technology Stack

- Frontend: React, Vite, CSS
- Backend: FastAPI, Pydantic
- Database: SQLite
- ML: scikit-learn, joblib
- Deployment: Docker Compose
- PWA: manifest, service worker, mobile-responsive UI

## Honest Limitations

- Weather API needs a real OpenWeatherMap key.
- Market prices need official Agmarknet/eNAM data.
- Gemini powers crop explanations, multilingual chat, and image screening when its backend API key is configured.
- Gemini image screening is advisory; a validated specialist disease model and expert confirmation remain important for production.
- The starter ML dataset is small and should be replaced with validated regional data before production.

## Strong Points

- Complete end-to-end prototype.
- Working backend APIs.
- Trainable ML pipeline.
- Persistent history.
- User accounts.
- Mobile-friendly PWA.
- Clear production integration path.
