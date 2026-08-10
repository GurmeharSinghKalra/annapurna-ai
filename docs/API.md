# API Reference

Base URL:

```text
http://127.0.0.1:8000
```

## Health

```http
GET /health
```

Returns service status and ML model availability.

## Crop Recommendations

```http
POST /recommendations
```

Body:

```json
{
  "farmer_name": "Demo Farmer",
  "phone": "9999999999",
  "location": "Sonipat, Haryana",
  "language": "English",
  "land_size": 2,
  "season": "Kharif",
  "soil_type": "Alluvial",
  "ph": 6.6,
  "nitrogen": 62,
  "phosphorus": 41,
  "potassium": 48,
  "temperature": 29,
  "humidity": 64,
  "rainfall": 115,
  "budget": 35000,
  "market_priority": "Balanced"
}
```

## Reports

```http
POST /reports/recommendation
```

Returns a text report for the submitted farm profile.

## Authentication

```http
POST /auth/register
POST /auth/login
```

Register body:

```json
{
  "name": "Demo Farmer",
  "phone": "9999999999",
  "password": "secret123",
  "language": "English",
  "location": "Sonipat, Haryana"
}
```

Login body:

```json
{
  "phone": "9999999999",
  "password": "secret123"
}
```

## Advisory And Data

```http
POST /weather
POST /soil
POST /market
POST /chat
POST /disease
```

`POST /recommendations` returns deterministic rankings plus an optional Gemini
`ai_explanation`. `POST /chat` returns `provider: gemini` when Gemini answered and
`local_fallback` otherwise. `POST /disease` accepts multipart fields `file` and optional
`crop`, returning structured Gemini screening fields (`prediction`, `confidence`,
`observations`, `advisory`, and `urgency`) when configured.

## History

```http
GET /history
POST /history
```

## Admin And Metadata

```http
GET /crops
GET /admin/summary
GET /integrations/status
```
# Complete farm analysis

`POST /analysis` is the primary proposal workflow. It accepts the same farm profile as
`POST /recommendations`, plus `previous_crop`, and returns:

- ranked crop recommendations;
- expected yield, cost, revenue, profit, margin, market trend, and sustainability score;
- weather data with a source label;
- soil-health scoring and pH/NPK actions;
- market outlook for the top three crops;
- a Gemini explanation when configured, with a local fallback otherwise.
