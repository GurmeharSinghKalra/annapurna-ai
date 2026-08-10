# API Reference

Base URL: `http://127.0.0.1:8000` · Interactive docs: `/docs`

## Authentication

Register or log in, then send the returned token as a bearer credential.

```http
POST /auth/register    201
POST /auth/login       200
POST /auth/logout      204   (requires Authorization)
GET  /auth/me          200   (requires Authorization)
```

Register body:

```json
{
  "name": "Demo Farmer",
  "phone": "9811100001",
  "password": "at-least-8-characters",
  "language": "English",
  "location": "Sonipat, Haryana"
}
```

Both register and login return:

```json
{
  "user": { "id": 1, "name": "...", "phone": "...", "language": "...", "location": "...", "created_at": "..." },
  "access_token": "…",
  "token_type": "bearer",
  "expires_at": "2026-08-25T12:00:00+00:00"
}
```

Authenticated requests:

```http
Authorization: Bearer <access_token>
```

Sessions are opaque tokens stored hashed, expire after `SESSION_TTL_HOURS`, and are
revoked by `POST /auth/logout`. Repeated failed logins from the same client are
throttled and answered with `429` plus a `Retry-After` header.

## The farm profile

Most endpoints take a `FarmProfile`. Every agronomic field is **required** — an
incomplete request is rejected with `422` rather than answered with defaults.

```json
{
  "location": "Sonipat, Haryana",
  "season": "Kharif",
  "previous_crop": "None",
  "soil_type": "Alluvial",
  "market_priority": "Balanced",
  "language": "English",
  "land_size": 2,
  "ph": 6.6,
  "nitrogen": 62,
  "phosphorus": 41,
  "potassium": 48,
  "temperature": 29,
  "humidity": 64,
  "rainfall": 115,
  "budget": 95000
}
```

`farmer_name` and `phone` are optional; a ranking does not need to know who is
asking, and reports omit the identity block when it is absent. Unknown fields and
out-of-range values are rejected. `rainfall` is the **seasonal** total in millimetres.

## Recommendations

```http
POST /recommendations
POST /analysis
```

Each recommendation carries reconciling economics:

| Field | Meaning |
| --- | --- |
| `expected_yield` | Quintal across the whole holding |
| `market_price` | Planning price per quintal |
| `estimated_revenue` | `expected_yield * market_price` |
| `estimated_cost` | Per-acre cost x land size |
| `expected_profit` | `estimated_revenue - estimated_cost` |
| `profit_margin` | `expected_profit / estimated_revenue` as a percentage |
| `budget_covers_cost` | Whether the stated budget funds the estimated cost |
| `budget_shortfall` | Rupees short, `0` when covered |
| `suitability` | 0–100, normalised against the maximum attainable score |
| `ml_influence` | Whether the trained model affected this crop, and how strongly |

Results are sorted by suitability, then expected profit, then crop name — a total
order, so ranking never depends on catalog position.

`POST /analysis` is the primary workflow. It returns ranked recommendations,
weather, soil health and actions, market outlook for the top three crops, an
optional Gemini explanation, and an `inputs_used` block naming the provenance of
each input:

```json
"inputs_used": {
  "temperature": 29, "humidity": 64, "rainfall": 115,
  "temperature_source": "farmer", "humidity_source": "farmer", "rainfall_source": "farmer"
}
```

Live weather replaces temperature and humidity when configured. Seasonal rainfall
always stays farmer-entered: upstream feeds report short-interval rain only, and
the two are not interchangeable.

## Advisory and data

```http
POST /weather
POST /soil
POST /market
POST /chat
POST /disease
POST /reports/recommendation
```

Every response carries a `source` label and a boolean `live` flag. An upstream
failure degrades to the labelled fallback with a `note`; it never returns 5xx.

`POST /chat` takes `{ "question": "...", "crop": "Maize" | null, "farm": {...} }` and
reports `provider` as `gemini` or `local_fallback`.

`POST /disease` accepts multipart `file` and optional `crop`. The image type is
determined from the file's own bytes, not the declared Content-Type: non-images are
rejected with `415`, empty uploads with `400`, and anything over `MAX_UPLOAD_BYTES`
with `413`. Without Gemini configured the response reports that no screening ran —
it does not fabricate a prediction.

`POST /reports/recommendation` returns `text/plain` as a file attachment.

## History

```http
GET  /history    (requires Authorization)
POST /history    (requires Authorization) 201
```

History is scoped to the authenticated account. One farmer can never read another's
saved plans.

## Metadata and admin

```http
GET /health
GET /crops
GET /integrations/status
GET /admin/summary        (requires X-Admin-Token)
```

`/admin/summary` returns `503` until `ADMIN_TOKEN` is configured, then `403` unless
the `X-Admin-Token` header matches. It reports model state including measured
cross-validated accuracy and whether that accuracy is high enough for the model to
influence ranking.

## Status codes

| Code | Meaning |
| --- | --- |
| `401` | Missing, invalid, or expired session |
| `403` | Admin token missing or wrong |
| `409` | Phone number already registered |
| `413` | Upload exceeds the size cap |
| `415` | Upload is not a recognised image |
| `422` | Request body fails validation |
| `429` | Too many failed sign-in attempts |
| `503` | Admin endpoints disabled (no `ADMIN_TOKEN`) |
