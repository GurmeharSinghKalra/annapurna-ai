# Testing

## Running

```bash
# Backend: 169 tests
cd backend
python -m pytest                      # all
python -m pytest tests/test_security.py -v
python -m pytest -k break_even

# Frontend: 38 tests
npm test                              # watch mode
npm test -- --run                     # once
```

Lint and format gates, which CI also runs:

```bash
cd backend && ruff check app scripts tests && ruff format --check app scripts tests
npm run lint
```

## The suite is hermetic, on purpose

The previous suite failed four tests the moment `AGMARKNET_API_KEY` was set, and made real DNS
and HTTPS calls to `api.data.gov.in`. It was green only on a machine with no credentials — the
one configuration nobody deploys — and it went red the day CI was handed real secrets.

`tests/conftest.py` now:

- pins the environment **before** the app is imported, so settings are deterministic;
- blocks outbound HTTP at the transport, so a stray real request fails loudly instead of hanging
  CI or silently passing. A test that needs a feed installs its own transport and marks itself
  `@pytest.mark.allow_http`;
- disables the Gemini client, so nothing touches a billing meter;
- drops and recreates the schema around each test, so ordering cannot make a test pass;
- clears the process-global rate limiter between tests.

CI deliberately sets all three API keys to dummy values to prove the suite's result does not
depend on them.

## What is covered

| File | Covers |
| --- | --- |
| `test_recommender.py` | Honest scoring, hard limiters, irrigation, sustainability, ranged economics, model governance |
| `test_finance.py` | Break-even stability, cash-flow arithmetic, scenario construction, category validation |
| `test_auth_and_records.py` | Registration, phone normalisation, token rotation and theft detection, cross-account isolation, cascade deletion |
| `test_security.py` | Every vulnerability the audit found, each named for what used to be possible |
| `test_integrations.py` | Weather and market behaviour with and without keys, caching, trend, prompt fencing, multilingual fallback |
| `test_api.py` | Route contracts, validation bounds, report content, OpenAPI integrity |
| `src/api.test.js` | Error translation, token refresh, storage guards |
| `src/farm.test.js` | Validation, API conversion, normalisation |
| `src/components.test.jsx` | Money formatting, charts with negative values, error boundary, async state |

## Regression tests name the bug

Security and correctness tests are named for the defect they prevent, so a failure says what
broke rather than only that something did. For example:

- `test_a_chunked_body_cannot_bypass_the_upload_limit`
- `test_the_pdf_shows_the_servers_numbers_not_the_clients`
- `test_break_even_price_is_stable_across_plot_sizes`
- `test_screening_refuses_rather_than_inventing_a_diagnosis`
- `test_an_unevaluated_model_is_refused`

## Not covered yet

- No end-to-end browser test. The highest-value one would be: complete the planner, run the
  analysis, build a budget, save a plan, sign in, confirm the plan is still there.
- No load test. The PDF route and the AI routes are the places where one would be informative.
- No visual regression testing.
