"""Windows portable launcher for Annapurna AI.

Serves the pre-built React client and the FastAPI API from a single local process.

The previous version was non-functional end to end. The client bundle is built with no
``VITE_API_URL``, so it calls ``/api/...``; this launcher mounted the API at the root and then
registered a catch-all that returned ``index.html`` for every unmatched GET. Every API call
therefore received an HTML page with status 200, so `response.ok` was true, `response.json()`
threw, and the app reported "backend offline" for every feature. The fix is to mount the API
under ``/api`` exactly as the nginx deployment does.

Runtime data (the SQLite database) is written beside the executable so plans survive a restart.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

HOST = "127.0.0.1"
PORT = 5173


def bundle_root() -> Path:
    """Where the read-only bundled files live (inside the EXE when frozen)."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def runtime_root() -> Path:
    """Where writable data lives: beside the EXE, or the repo root when run from source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


RUNTIME_ROOT = runtime_root()
BUNDLE_ROOT = bundle_root()
FRONTEND_DIR = BUNDLE_ROOT / "frontend"
DATA_DIR = RUNTIME_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configure the app before importing it: settings are read when the module loads.
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(DATA_DIR / 'annapurna.db').as_posix()}")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")
os.environ.setdefault("APP_ENV", "portable")
os.environ.setdefault("CORS_ORIGINS", f"http://{HOST}:{PORT}")
# Optional real API keys come from a .env the user creates beside the EXE.
_env_file = RUNTIME_ROOT / ".env"
if _env_file.is_file():
    from dotenv import load_dotenv

    load_dotenv(_env_file, override=True)

from app.main import app as api_app  # noqa: E402  - imported after the environment is prepared

@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run the API's own startup and shutdown.

    Starlette does not run a mounted sub-application's lifespan, so without this the database
    schema is never created and every account or market-cache query fails with "no such table".
    """
    async with api_app.router.lifespan_context(api_app):
        yield


app = FastAPI(title="Annapurna AI (portable)", docs_url=None, redoc_url=None, lifespan=lifespan)

# The built client calls `/api/...`, so the API must live there. This mirrors the nginx
# deployment exactly, which keeps the single-process build and the container build identical
# from the browser's point of view.
app.mount("/api", api_app)

if (FRONTEND_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    """Serve a bundled file when it exists, otherwise the SPA shell."""
    index = FRONTEND_DIR / "index.html"
    if not index.is_file():
        return JSONResponse(
            status_code=500,
            content={"detail": "The bundled web interface is missing from this package."},
        )
    if path:
        candidate = (FRONTEND_DIR / path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIR.resolve())
        except ValueError:
            # A traversal attempt such as ../../secret falls back to the shell.
            return FileResponse(index)
        if candidate.is_file():
            return FileResponse(candidate)
    return FileResponse(index)


def open_browser() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}", new=1)


def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    print(f"Annapurna AI is starting at http://{HOST}:{PORT}")
    print(f"Your data is stored in: {DATA_DIR}")
    threading.Timer(1.5, open_browser).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
