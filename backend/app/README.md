# Application service modules

Each module has one focused role so a recommendation can be understood, tested, and
extended without coupling the UI to any one provider.

| Module | Role | Key entry points |
| --- | --- | --- |
| `main.py` | FastAPI app, routes, auth dependencies, lifespan, CORS. | `/analysis`, `/recommendations`, `/chat`, `/disease`, auth, reports, history. |
| `schemas.py` | Request and response contracts, and input validation. | `FarmProfile`, `Recommendation`, `ChatRequest`, `AuthResponse`. |
| `security.py` | Password hashing, session tokens, login throttling. | `hash_password`, `verify_password`, `RateLimiter`. |
| `database.py` | SQLite persistence, migrations, users, sessions, history. | `get_connection`, `create_user`, `create_session`, `resolve_session`. |
| `recommender.py` | Crop scoring, rotation, economics, sustainability. | `recommend`, `crop_catalog`. |
| `ml_model.py` | Cached loading and accuracy-gated prediction. | `predict_crop`, `model_status`. |
| `integrations.py` | Weather, soil, and market adapters with labelled fallbacks. | `fetch_weather`, `soil_profile`, `market_profile`. |
| `gemini_service.py` | Gemini boundary and prompt hardening. | `GeminiService`. |
| `advisory.py` | Offline English, Hindi, Punjabi, and Haryanvi advisory text. | `localized_chat_answer`. |
| `uploads.py` | Image type sniffing and upload size limits. | `read_image_upload`. |
| `reports.py` | Plain-text crop-plan export. | `recommendation_report`. |
| `config.py` | Environment-driven settings, read once per process. | `get_settings`. |

## Extension rules

- Keep crop ranking deterministic in `recommender.py`. Gemini may explain it but
  must never alter the order.
- Never quote a derived figure that cannot be recomputed from figures already shown.
- Add an external provider inside `integrations.py`, and keep both the source label
  and a fallback that engages on failure rather than propagating an error.
- Add new fields to `schemas.py` first, then wire them through the API and frontend.
- Read configuration through `get_settings()`, never `os.getenv` at import time.
- Fence untrusted farmer text in any Gemini prompt; treat it as data, not instruction.
- Treat disease results as screening guidance, not laboratory-grade diagnosis.
- Do not commit API keys, uploaded images, passwords, or generated SQLite/model files.
