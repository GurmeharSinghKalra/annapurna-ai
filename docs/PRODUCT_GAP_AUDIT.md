# Product gap audit

This document records the boundary between the working Annapurna AI prototype and the work needed
to operate it as a reliable farmer-planning tool. It is intentionally ordered by product value and
dependency, not by technical novelty.

## Working end-to-end today

- Farm profile to crop recommendation, rotation context, unit-consistent economics, soil actions, weather status,
  market baseline, sustainability, and report export.
- Season Finance: category budget, actual expense replacement, browser-persisted cost tracking,
  cash flow, break-even price, budget gap, downside scenarios, and finance export.
- Source-labelled Gemini advisory and crop image screening, with local fallbacks.
- Browser-only use remains possible when the API is offline for core crop ranking.

## Current boundaries

| Area | Current state | What must change before a public production rollout |
| --- | --- | --- |
| Crop/financial data | Crop costs, yield, and price trends are planning baselines. An optional source-labelled JSON market-feed adapter or farmer-verified local mandi price can replace the price for a plan. | Connect and validate an official mandi feed, then add district/crop cost and yield datasets. |
| Weather | Uses OpenWeatherMap only when a key and network request work. | Add forecast, geocoding, cache, retry/observability, and regional advisories. |
| Soil | Farmer-entered pH/NPK rules. | Add coordinates, consent, SoilGrids/soil-test integrations, and regional validation. |
| Finance | No banking, lending, credit, or payment data. Expense tracking is browser persisted. | Add explicit farmer data ownership, encrypted server persistence, and real cost datasets only if the product needs shared records. |
| Chatbot | Gemini answers from current farm context and can use the current non-sensitive season-finance snapshot. | Add curated knowledge retrieval, citations, abuse/rate limits, feedback, chat history, and agriculture-expert review. |
| Disease screening | Gemini visual screening only. | Add labelled disease dataset, validated model, confidence thresholds, and expert escalation protocol. |
| Identity | The active tool is deliberately no-account: saved plans and finance tracking are browser-local. | Decide whether multi-device use warrants user accounts and scoped data access. |
| Deployment | Docker build definitions exist. | Add production hosting, HTTPS, secrets manager, monitoring, backups, and incident handling. |

## Approved build order

1. **Season Finance** — complete as a planning feature; no credit or lending scope.
2. **Live data layer** — market prices first, then weather and soil enrichment.
3. **Finance-aware Farm Copilot** — upgrade the existing Gemini advisor after the live data layer
   is trustworthy; do not build a second chatbot.
4. **Persistence/identity decision** — only when real multi-device or multi-farmer records are a
   product requirement.
5. **Public deployment hardening** — production security, monitoring, backups, and privacy work.

## Non-negotiable product safeguards

- Label planning baselines and manual values clearly.
- Treat revenue, yield, price, disease, and AI responses as estimates, never guarantees.
- Do not offer loans, credit scores, investment recommendations, or use bank-account data without
  a regulated partner and a separate compliance design.
- Keep API keys on the backend only.
