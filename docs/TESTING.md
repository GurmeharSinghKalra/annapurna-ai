# Testing Guide

## Automated checks

From the repository root:

```bash
npm run lint && npm run build
```

From `backend/` with the virtualenv active:

```bash
python scripts/train_model.py && python -m pytest -q
```

Docker:

```bash
docker compose config --quiet && docker compose build
```

All three run in CI on every push (`.github/workflows/ci.yml`).

## What the backend suite covers

96 tests across four files. The suite is hermetic: it writes to a temporary
database and model directory, never to `backend/data/` or `backend/models/`, and
running it twice in a row gives identical results. CI fails the build if a test run
leaves a database behind in the project tree.

| File | Focus |
| --- | --- |
| `tests/test_auth.py` | Registration, login, sessions, logout, throttling, password hashing and legacy-hash upgrade |
| `tests/test_api.py` | Input validation, history ownership, admin gating, weather fallbacks, upload limits, chat, reports |
| `tests/test_recommender.py` | Economic and scoring invariants swept across randomised farm profiles |
| `tests/test_ml_model.py` | Training metrics, accuracy gating, model caching, corrupt artifacts |

Several tests exist specifically to stop old defects returning:

- Revenue always equals `expected_yield * market_price`, and profit always equals
  revenue minus cost, checked across 60 randomised profiles.
- A fixed budget must not stay "sufficient" as land size grows.
- Fewer than 2% of random profiles may reach the top of the suitability scale.
- An upstream weather failure must degrade to a labelled fallback, and the API key
  must not appear in the logs.
- A non-image upload must be rejected even when it declares `image/png`.
- The model must be read from disk once, not on every request.
- Database connections must be closed after use, including when the body raises.

Gemini is disabled for the whole suite by an autouse fixture, and API keys are
forced empty before the app is imported so a developer's real `.env` cannot leak
live credentials into a test run.

## Manual frontend checklist

Start both services, then open <http://127.0.0.1:5173>.

1. Visit `/dashboard` while signed out — you should be asked to sign in, not shown a workspace.
2. Register an account. A failed registration must leave you signed out.
3. In the crop planner, change season, soil, pH, rainfall, budget, and priority.
4. Run the complete analysis. Confirm the ranked cards, reasons, and cautions appear.
5. On Insights, check that revenue equals the stated yield times the stated price,
   and that net return equals revenue minus cost.
6. Set a budget below the top crop's cost and confirm the shortfall warning appears.
7. Change an input without re-running, and confirm the "inputs changed" banner appears.
8. Save a plan, then confirm it appears under Saved plans.
9. Sign out and back in; your saved plans should still be there, and only yours.
10. Upload a non-image file to Disease scan and confirm it is refused.
11. Ask the advisor a question.
12. Click Report and confirm a text file downloads.
13. Stop the backend, reload, and confirm the cached analysis appears with its age
    and a re-run button — not a different recommendation.

## Manual backend URLs

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/crops
http://127.0.0.1:8000/integrations/status
http://127.0.0.1:8000/docs
```

`/admin/summary` needs `ADMIN_TOKEN` set and sent as `X-Admin-Token`.
