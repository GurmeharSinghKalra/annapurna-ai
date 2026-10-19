# Application service modules

This directory contains the domain logic behind Annapurna AI. Each module has one focused role so the recommendation result can be understood, tested, and extended without coupling the UI to one provider.

| Module | Role | Key entry points |
| --- | --- | --- |
| `main.py` | FastAPI application and REST endpoints. | `/analysis`, `/recommendations`, `/finance/season-plan`, `/chat`, `/disease`, reports. |
| `schemas.py` | Request and response contracts. | `FarmProfile`, `Recommendation`, `ChatRequest`. |
| `recommender.py` | Transparent crop scoring, prior-crop rotation, economics, market baseline, and sustainability metrics. | `recommend`, `crop_catalog`. |
| `ml_model.py` | Cached optional scikit-learn classifier loader with a rule-based failure fallback. | `predict_crop`, `model_available`. |
| `integrations.py` | Weather, soil-health, market, and integration-status adapters. | `fetch_weather`, `soil_profile`, `market_profile`. |
| `finance.py` | Season cost allocation, cash flow, break-even, and scenario calculations. | `season_financial_plan`. |
| `gemini_service.py` | Gemini explanation, multilingual chat, and image-screening boundary. | `GeminiService`. |
| `advisory.py` | Offline English, Hindi, Punjabi, and Haryanvi advisory responses. | `localized_chat_answer`. |
| `database.py` | Legacy prototype persistence module; it is not exposed by the current no-account API. | No active route. |
| `reports.py` | Plain-text crop-plan export generated from the recommendation engine. | `recommendation_report`. |
| `config.py` | Environment-based settings. | `settings`. |

## Extension rules

- Keep crop ranking deterministic in `recommender.py`; Gemini may explain it but must not alter the order.
- Add an external data provider inside `integrations.py` and retain a clear source label and fallback.
- Add new input/output fields to `schemas.py` first, then wire them through the API and frontend.
- Treat disease results as screening guidance, not laboratory-grade diagnosis.
- Do not store API keys, uploaded images, passwords, or generated SQLite/model files in Git.
