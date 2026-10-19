"""Generate docs/API.md from the live OpenAPI schema.

Keeping the route table generated means it cannot describe a route that does not exist, which is
how the previous hand-written reference ended up documenting one set of endpoints while the code
served another. Run from the backend directory:

    python scripts/generate_api_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "API.md"

TAG_ORDER = ["operations", "planning", "reports", "advisory", "auth", "records"]
TAG_NOTES = {
    "operations": "Health, readiness, and an honest account of which external services are connected. No authentication.",
    "planning": "The core workflow. Every route here works without an account.",
    "reports": (
        "Downloadable reports. The server recomputes the recommendation from the farm profile, so a "
        "client cannot make a branded report claim numbers of its own choosing."
    ),
    "advisory": (
        "AI-backed routes, rate limited per client. When the provider is not configured they return "
        "503 or a clearly-labelled template rather than inventing an answer."
    ),
    "auth": "Farmer accounts. Entirely optional: no planning route requires one.",
    "records": "Durable storage, scoped to the signed-in account. Every query filters by owner.",
}
AUTH_REQUIRED = {"/auth/me", "/auth/password"}

PREAMBLE = """# API reference

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
"""

EPILOGUE = """
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
| `verdict` | `strong match` \\| `good match` \\| `workable with care` \\| `marginal` \\| `not recommended` |
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
"""


def main() -> None:
    schema = app.openapi()
    by_tag: dict[str, list] = {}
    for path, methods in sorted(schema["paths"].items()):
        for method, spec in methods.items():
            tag = (spec.get("tags") or ["other"])[0]
            by_tag.setdefault(tag, []).append((method.upper(), path, spec))

    lines = [PREAMBLE]
    for tag in TAG_ORDER + [t for t in by_tag if t not in TAG_ORDER]:
        entries = by_tag.get(tag)
        if not entries:
            continue
        lines.append(f"\n## {tag.replace('_', ' ').title()}\n")
        lines.append(f"{TAG_NOTES.get(tag, '')}\n")
        lines.append("| Method | Path | Purpose | Auth |")
        lines.append("| --- | --- | --- | --- |")
        for method, path, spec in entries:
            summary = (spec.get("summary") or "").strip()
            described = (spec.get("description") or "").strip().split("\n")[0]
            purpose = (described or summary or "—").replace("|", "\\|")
            needs_auth = "Yes" if tag == "records" or path in AUTH_REQUIRED else "No"
            lines.append(f"| `{method}` | `{path}` | {purpose} | {needs_auth} |")
        lines.append("")

    lines.append(EPILOGUE)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
