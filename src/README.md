# Frontend module

`src/` contains the React/Vite client for Annapurna AI. The client is one shared farm workspace: every page receives the same current farm profile so the crop planner, insights, disease screen, advisor, records, and report export describe the same decision.

## Files

| File | Responsibility |
| --- | --- |
| `main.jsx` | Routes, UI components, local fallback ranking, API calls, account state, report export, and accessibility labels. |
| `styles.css` | Responsive visual system, typography, desktop sidebar, mobile navigation, panels, inputs, and state styles. |

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page explaining the product and its safeguards. |
| `/about` | Project scope, architecture, and responsible-use information. |
| `/register`, `/login` | Farmer account registration and sign-in. |
| `/dashboard` | Current crop recommendation and quick actions. |
| `/planner` | Farm inputs, prior-crop rotation context, ranked crop options, and complete analysis trigger. |
| `/insights` | Soil health, weather, economics, market outlook, rotation, and sustainability output. |
| `/disease` | Gemini-backed crop image screening with a safe fallback. |
| `/advisor` | Context-aware multilingual agricultural chat. |
| `/records` | Saved recommendation history. |
| `/settings` | Integration status, exports, and safety information. |

## Data flow

1. The form is converted to the FastAPI `FarmProfile` shape by `toApiFarm`.
2. The planner calls `POST /analysis` through `API_BASE`.
3. The returned recommendations are normalized for presentation components.
4. The Insights page reads weather, soil, and market objects from that same analysis.
5. When the API is unavailable, local deterministic ranking and advisory text keep the interface usable.

Set `VITE_API_URL` when deploying the frontend separately. Without it, the development client uses `http://127.0.0.1:8000`.

## Local verification

```powershell
npm install
npm run dev
npm run build
```

For manual acceptance, open `/planner`, select a previous crop, choose **Run complete analysis**, then confirm that `/insights` presents source-labelled weather, soil, market, economics, and sustainability information.
