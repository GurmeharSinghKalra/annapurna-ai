# Defense Guide

## One-line explanation

Annapurna AI is an AI-based crop recommendation and agricultural advisory system
that helps farmers choose suitable crops using soil, weather, nutrient, market, and
sustainability factors — and shows its working.

## Problem statement

Farmers often lack localized, data-driven guidance for crop selection. Generic
advisory systems do not consider soil nutrients, weather, rainfall, crop rotation,
market priority, budget, and language accessibility together.

## What to demonstrate

1. Try to open `/dashboard` while signed out — you are asked to sign in.
2. Register a farmer account; show the bearer token in the network tab.
3. Change farm conditions in the crop planner.
4. Run the complete analysis; show ranked crops with reasons and cautions.
5. On Insights, show that revenue equals yield times price, and net return equals
   revenue minus cost. Every figure on screen can be recomputed from the others.
6. Set a low budget and show the shortfall warning and the ranking penalty.
7. Change the previous crop and show the ranking respond.
8. Save a plan; sign in as a second farmer and show the first farmer's plans are
   not visible.
9. Show the Gemini advisor and the multimodal disease screening.
10. Upload a non-image file to disease screening and show it refused.
11. Stop the backend and reload: the cached analysis appears with its age and a
    re-run button, rather than different advice.
12. Show `/admin/summary` returning 503 without a token, then working with one.

## Technology stack

- Frontend: React 19, Vite 7, CSS
- Backend: FastAPI, Pydantic v2
- Database: SQLite (users, sessions, history)
- ML: scikit-learn, joblib
- Deployment: Docker Compose, nginx
- CI: GitHub Actions (lint, build, tests, container smoke test)

## Design decisions worth explaining

**Ranking exists in exactly one place.** An earlier version scored crops in the
browser as well as the server. The copies drifted, and after a wheat crop the
offline client recommended planting wheat again while the server penalised it.
There is now one implementation; when offline the client replays the server's last
real answer, labelled with its age.

**Revenue is derived, never stored.** It is always `yield x price`. Previously
revenue was `cost + profit`, which contradicted the price printed beside it by up
to 25%.

**Scores are normalised, not clipped.** Clipping at a ceiling pinned 16% of farm
profiles to the same top score, so the ranking stopped discriminating. Scores are
now normalised against the maximum attainable, and ties break deterministically on
profit and then name.

**The model has to earn its vote.** Training measures stratified cross-validated
accuracy and writes it beside the artifact. Below 60% the model is loaded, reported,
and ignored. Its influence is scaled by that accuracy, so a thin dataset cannot
outvote agronomy.

**Fallbacks are labelled, not disguised.** Every data response carries `source` and
`live`. Without a Gemini key, disease screening says no screening ran instead of
returning a fabricated 72%-confidence prediction.

## Honest limitations

- The starter ML dataset is 24 rows with cross-validated accuracy around 0.63. It
  demonstrates the pipeline; it is not a basis for real decisions.
- Market prices are a planning baseline until official Agmarknet/eNAM feeds are
  connected.
- Crop cost, yield, and price figures are planning estimates, not validated survey data.
- Weather needs a real OpenWeatherMap key; without one the farmer's own readings are
  used and labelled.
- Disease screening is advisory and needs expert confirmation.
- Rate limiting is per process; SQLite suits a prototype, not production traffic.

## Strong points

- End-to-end prototype with real authentication and per-farmer data isolation.
- Internally consistent economics that a farmer can check by hand.
- Explainable ranking: every score comes with reasons and cautions.
- 96 automated backend tests, many of them regression tests for specific defects.
- Reproducible containerised deployment verified in CI.
