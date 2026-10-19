# Windows portable build

Produces a folder containing `AnnapurnaAI.exe`, which serves the built web interface and the API
from a single local process. No Python, Node or Docker needed on the target machine.

## Build

From a Windows machine with the backend virtual environment already created:

```powershell
cd distribution
.\build_windows_portable.ps1
```

Output: `release\Annapurna-AI-Windows\`, plus a zip of the same.

## Run

Double-click `START_ANNAPURNA_AI.cmd`. The app opens at <http://127.0.0.1:5173>.
`STOP_ANNAPURNA_AI.cmd` shuts it down.

## Your data

Saved plans, season budgets and accounts live in a SQLite database in the `data` folder beside
the executable. Copy that folder to move or back up your records. Deleting it erases them.

## API keys

Everything works without keys; a feature that needs one says so on screen rather than showing
placeholder data. To enable them, create a file named `.env` in the `Annapurna-AI-Windows`
folder:

```
GEMINI_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
AGMARKNET_API_KEY=your_key
```

## A note on how this used to be broken

The built web interface calls `/api/...`. The earlier launcher mounted the API at the root and
then served `index.html` for every unmatched path, so every API call received an HTML page with
status 200: the browser's `response.ok` was true, parsing the body threw, and the app reported
"backend offline" for every feature. The portable build was non-functional end to end.

The launcher now mounts the API under `/api`, exactly as the nginx deployment does, and runs the
API's startup so the database schema exists. `test_portable.py` covers both.
