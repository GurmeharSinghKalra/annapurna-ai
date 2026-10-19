# Architecture

## Shape

```
Browser ──► nginx (frontend container) ──► /api/* ──► FastAPI ──► PostgreSQL
                     │                                   │
              static React build                         ├─► AGMARKNET (data.gov.in)
                                                         ├─► OpenWeatherMap
                                                         └─► Google Gemini
```

In development the Vite dev server plays nginx's part, proxying `/api` to port 8000. The browser
therefore makes same-origin calls in both environments, and `API_BASE` is `/api` everywhere.

## The ranking

`recommender.py` scores each crop out of 100 from weighted components, then applies **hard
limiters** that cap the score regardless of how well everything else fits.

| Component | Weight |
| --- | --- |
| Season match | 22 |
| Water availability | 20 |
| Soil type | 16 |
| pH | 14 |
| Temperature | 12 |
| Nutrients | 11 |
| Market priority | 5 |
| Rotation | ±10 |
| Trained model agreement | up to 6, scaled by measured accuracy |

Limiters and their caps:

| Condition | Cap |
| --- | --- |
| Out of season (non-annual crop) | 25 |
| High-water crop on a rainfed field | 28 |
| Water shortfall over 40% of need | 30 |
| Temperature far outside range | 38 |
| pH far outside range | 40 |
| Very low nutrients | 45 |
| Soil type mismatch | 62 |

The lowest applicable cap wins, and every limiter is returned in `limiters` so the farmer reads
the single reason rather than an unexplained number. This is the mechanism that lets the product
say "not recommended" — the previous version clamped suitability to a floor of 36, so a field
with pH 14, no nutrients and no rainfall still showed every crop as 36% suitable.

### Why hard limiters rather than larger weights

Some conditions are disqualifying rather than unfavourable. Wheat in kharif is not a slightly
worse wheat; it is the wrong season. A weighted model can always be outvoted by enough other
components, which is how an out-of-season crop can surface as a recommendation. A cap cannot be
outvoted.

## Economics

Yield and cost are ranges, scaled by land size and multiplied by a price whose origin is always
stated. The poor case pairs low yield with high cost; the good case the reverse. The headline
figures are the typical case, and the UI shows all three.

Yield is never rounded before the money is calculated. Rounding first made break-even price
non-monotonic across plot sizes: 0.1 and 0.2 acre of mustard both reported ₹2,200/quintal while
0.5 acre reported ₹1,833.

## Market data

`market_data.py` resolves a crop to AGMARKNET's own commodity spellings — the dataset calls rice
`Paddy(Dhan)(Common)`, so an exact-match filter on "Rice" returns nothing — and narrows from
district to state to nationwide until a price is found.

Prices are cached per `(commodity, state, district)` so a hundred farmers in one district cost
one upstream request, and each observation is appended to a history table. Price direction is
**measured** from that history; until there are enough points the API says
`not enough recorded history yet` rather than returning an invented percentage.

## Weather

`weather.py` geocodes the location, fetches current conditions and a five-day rain outlook, and
caches both. Two rules it enforces:

- Farmer-typed numbers are never presented as a weather reading. With no provider configured the
  response carries `live: false` and is labelled as the farmer's own input.
- `rain.1h` (millimetres in the last hour) is never written into the seasonal rainfall field. It
  is reported separately as `recent_rain_mm_1h`, alongside `forecast_rain_mm_5d`.

## AI

`gemini_service.py` fences all farmer-supplied text in `<farmer_input>` tags and instructs the
model that nothing inside them can change its instructions. Model ids are retired on a schedule,
so a rejected id falls back through a short list and the working one is remembered rather than
disabling every AI feature until someone edits the environment.

When Gemini is unavailable, chat returns a template that states it is not an answer, and image
screening returns 503. It does not guess: the previous version returned "leaf stress detected" at
0.72 confidence for any image, including a blank one.

## Data model

| Table | Holds |
| --- | --- |
| `farmers` | Accounts. Phone is the login key, argon2 password hash |
| `farm_profiles` | Named sets of field conditions, reused across seasons |
| `saved_plans` | Recommendation snapshots, self-contained so they still read correctly after the crop table changes |
| `season_finance_plans` | Season budgets, one live plan per crop per farmer |
| `refresh_sessions` | Long-lived logins, stored as hashes so a database leak cannot replay them |
| `market_price_snapshots` | The mandi price cache |
| `market_price_history` | Daily price points, for measuring trend |

Everything a farmer creates cascades from their `farmers` row, so account deletion is one
statement rather than a manual sweep.

## Authentication

Short-lived JWT access tokens plus rotating refresh tokens. A refresh token is usable exactly
once; replaying a spent one is treated as theft and revokes every session for that account.
Tokens travel in the `Authorization` header, never cookies, so CORS does not allow credentials.

Accounts are optional throughout. Every planning route works signed out; an account only adds
durable, multi-device storage.

## Request handling

- A request id on every response, and in every log line.
- Body caps enforced **while the body streams**, so a chunked request cannot bypass a
  `Content-Length` check.
- PDF rendering runs on a thread pool, because laying out a document is CPU-bound and would
  otherwise block the event loop for every other request on the worker.
- Unhandled exceptions return a generic message plus the request id; the detail goes to the log.
- In-process sliding-window rate limiting, keyed by account or peer address. `X-Forwarded-For` is
  deliberately ignored, because it is client-supplied and would make the limiter useless.

## Deliberate limits

- The rate limiter is per-process, so it is correct for one API replica. `/health` says so.
- There is no background job runner; the price cache fills on demand.
- There is no email delivery, so password reset is not implemented.
