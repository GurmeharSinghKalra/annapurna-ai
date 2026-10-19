# API reference

The route table below is generated from the running application's OpenAPI schema, so it cannot
describe a route that does not exist. Regenerate it with:

```bash
cd backend && python scripts/generate_api_docs.py
```

Base URL in development: `http://127.0.0.1:8000`. Behind the frontend container: `/api`.
Interactive documentation is served at `/docs` while the API is running.

## Conventions

- Request and response bodies are JSON unless stated otherwise.
- Validation failures return `422` with a `detail` array naming each offending field.
- Every response carries an `X-Request-ID` header; quote it when reporting a problem.
- Rate-limited routes return `429` with a `Retry-After` header.
- Request bodies are capped (256 KB for JSON, 8 MB for an image upload) and the cap is enforced
  while the body streams, so a chunked request cannot bypass it.
- Authenticated routes expect `Authorization: Bearer <access_token>`. Tokens are never cookies,
  and the API does not accept credentials cross-origin.

---


## Operations

Health, readiness, and an honest account of which external services are connected. No authentication.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `GET` | `/admin/summary` | Admin Summary | No |
| `GET` | `/crops` | Crops | No |
| `GET` | `/health` | Liveness plus a description of which capabilities are actually available. | No |
| `GET` | `/integrations/status` | Integrations | No |
| `GET` | `/readyz` | Readiness: fails when a dependency the API cannot serve without is down. | No |


## Planning

The core workflow. Every route here works without an account.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `POST` | `/analysis` | The full workflow: weather, soil, ranked crops, rotation, market and an AI explanation. | No |
| `POST` | `/finance/season-plan` | Financial Plan | No |
| `POST` | `/market` | Market | No |
| `POST` | `/recommendations` | Crop Recommendations | No |
| `POST` | `/soil` | Soil | No |
| `POST` | `/weather` | Weather | No |


## Reports

Downloadable reports. The server recomputes the recommendation from the farm profile, so a client cannot make a branded report claim numbers of its own choosing.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `POST` | `/reports/pdf` | Report Pdf | No |
| `POST` | `/reports/recommendation` | Report | No |


## Advisory

AI-backed routes, rate limited per client. When the provider is not configured they return 503 or a clearly-labelled template rather than inventing an answer.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `POST` | `/chat` | Chat | No |
| `POST` | `/disease` | Disease | No |


## Auth

Farmer accounts. Entirely optional: no planning route requires one.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Login | No |
| `POST` | `/auth/logout` | Logout | No |
| `GET` | `/auth/me` | Me | Yes |
| `DELETE` | `/auth/me` | Delete the account and every record owned by it, immediately and irreversibly. | Yes |
| `PATCH` | `/auth/me` | Update Me | Yes |
| `POST` | `/auth/password` | Change Password | Yes |
| `POST` | `/auth/refresh` | Refresh | No |
| `POST` | `/auth/register` | Register | No |


## Records

Durable storage, scoped to the signed-in account. Every query filters by owner.

| Method | Path | Purpose | Auth |
| --- | --- | --- | --- |
| `GET` | `/finance/plans` | List Finance Plans | Yes |
| `POST` | `/finance/plans` | Save Finance Plan | Yes |
| `DELETE` | `/finance/plans/{plan_id}` | Delete Finance Plan | Yes |
| `POST` | `/plans` | Save Plan | Yes |
| `GET` | `/plans` | List Plans | Yes |
| `GET` | `/plans/{plan_id}` | Get Plan | Yes |
| `DELETE` | `/plans/{plan_id}` | Delete Plan | Yes |
| `GET` | `/profiles` | List Profiles | Yes |
| `PUT` | `/profiles` | Create or replace a named farm profile, so field conditions survive a browser change. | Yes |
| `DELETE` | `/profiles/{profile_id}` | Delete Profile | Yes |


---

## Core shapes

### FarmProfile

Sent to every planning route. All fields are required by the UI; the API supplies defaults.

| Field | Type | Range | Notes |
| --- | --- | --- | --- |
| `farmer_name` | string | 1-80 chars | |
| `location` | string | 2-120 chars | `District, State`, used for weather and mandi lookup |
| `language` | enum | English, Hindi, Punjabi, Haryanvi | Advisory reply language |
| `land_size` | number | 0.1-2000 | Acres |
| `season` | enum | Kharif, Rabi, Annual | |
| `previous_crop` | enum | `None` or a catalogue crop | Drives rotation scoring |
| `soil_type` | enum | Alluvial, Clayey, Loamy, Sandy loam, Black | |
| `irrigation` | enum | Rainfed, Limited, Assured | Decides whether a thirsty crop is possible at all |
| `ph` | number | 3-10 | |
| `nitrogen` / `phosphorus` / `potassium` | number | 0-100 | Relative soil-health index, not kg/ha |
| `temperature` | number | -10 to 55 | Mean growing-season temperature, °C |
| `humidity` | number | 0-100 | Percent |
| `rainfall` | number | 0-5000 | **Total for the whole season, in mm** — not per hour or per day |
| `budget` | number | 0-100000000 | INR |
| `market_priority` | enum | Balanced, Profit, Sustainability, Water saving | |

### Recommendation

| Field | Meaning |
| --- | --- |
| `suitability` | 0-100, with no artificial floor |
| `verdict` | `strong match` \| `good match` \| `workable with care` \| `marginal` \| `not recommended` |
| `limiters` | Disqualifying conditions, each of which caps the score on its own |
| `reasons` / `cautions` | Why it fits, and what to watch |
| `economics` | `expected_yield_quintal`, `estimated_cost_inr`, `estimated_revenue_inr`, `expected_profit_inr`, each `{low, typical, high}` |
| `market_price` + `price_basis` | The price used, and whether it is a live mandi price or an announced MSP |
| `duration_days` | Sowing to harvest |
| `sustainability_score` | 0-100, responding to the crop *and* the field |
| `sources` | Citations for the figures used |

The top-level `expected_profit`, `expected_yield`, `estimated_cost` and `estimated_revenue`
fields are the typical case from `economics`, provided for convenience.

## Errors

| Status | Meaning |
| --- | --- |
| `401` | Missing, expired or revoked token. Refresh, or sign in again. |
| `409` | Conflicts with something already stored (duplicate phone, storage limit reached). |
| `413` | Request body or upload exceeds the cap. |
| `415` | Unsupported upload type. Send PNG, JPEG or WebP. |
| `422` | Validation failed, or a named crop or expense category is not one the product covers. |
| `429` | Rate limited. Wait for `Retry-After` seconds. |
| `503` | A feature needs an API key that is not configured, or the database is unreachable. The `detail` names what is missing. |
