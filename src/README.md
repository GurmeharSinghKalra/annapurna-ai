# Frontend module

`src/` contains the React/Vite client. It is one shared farm workspace: every page
reads the same server-produced analysis, so the planner, insights, disease screen,
advisor, records, and report all describe the same decision.

**The client never ranks crops.** An earlier version scored crops in the browser as
well as on the server, and the two drifted into contradicting each other. Ranking
now happens only in `backend/app/recommender.py`.

## Files

| File | Responsibility |
| --- | --- |
| `main.jsx` | Routes, route guards, UI components, page state, and rendering. |
| `api.js` | Network boundary: bearer tokens, error normalisation, session storage, analysis cache. |
| `styles.css` | Responsive visual system, panels, inputs, and state styles. |

## Routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | public | Landing page. |
| `/about` | public | Project scope and responsible-use information. |
| `/register`, `/login` | public | Account registration and sign-in. |
| `/dashboard` | account | Current recommendation and quick actions. |
| `/planner` | account | Farm inputs, rotation context, ranked crops, analysis trigger. |
| `/insights` | account | Soil, weather, economics, market, rotation, sustainability. |
| `/disease` | account | Crop image screening. |
| `/advisor` | account | Context-aware multilingual chat. |
| `/records` | account | Saved plans for the signed-in farmer. |
| `/settings` | account | Integration status, exports, safety information. |

Account routes render a sign-in prompt when there is no session. The server enforces
the same boundary; the client guard is convenience, not security.

## Data flow

1. `toApiFarm` converts the camelCase form state into the API contract.
2. **Run complete analysis** calls `POST /analysis` through `API_BASE`.
3. The response is held in one `analysis` state object and cached in `localStorage`.
4. Every page reads from that object; none of them recompute anything.
5. When the API is unreachable, the cached analysis is replayed with its age and a
   re-run button. Changing an input marks the analysis stale rather than clearing it.

## Auth

`api.js` attaches `Authorization: Bearer <token>` to authenticated calls. Any `401`
clears the stored session and returns the user to sign-in. A failed sign-in leaves
the user signed out — it never fabricates a local session.

## Configuration

`VITE_API_URL` sets the API base and defaults to `http://127.0.0.1:8000`. Vite
inlines it at build time, so it must be set before `npm run build`.

## Local verification

```bash
npm install
npm run dev
npm run lint
npm run build
```
