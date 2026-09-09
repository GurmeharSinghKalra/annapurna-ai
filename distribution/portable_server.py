"""Windows portable launcher for Annapurna AI.

The executable produced from this script serves the pre-built React client and
FastAPI API from one local process. Runtime data stays beside the executable so
saved plans survive application restarts.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


RUNTIME_ROOT = runtime_root()
BUNDLE_ROOT = bundle_root()
FRONTEND_DIR = BUNDLE_ROOT / "frontend"

# Optional real API keys are read from a user-created .env beside the EXE.
load_dotenv(RUNTIME_ROOT / ".env")

# The existing database module computes paths at import time. Point it at a
# writable sibling folder before FastAPI imports and initializes the database.
from app import database  # noqa: E402

database.DATA_DIR = RUNTIME_ROOT / "data"
database.DB_PATH = database.DATA_DIR / "annapurna_ai.sqlite"

from app.main import app  # noqa: E402


if (FRONTEND_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="frontend-assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    candidate = (FRONTEND_DIR / path).resolve()
    try:
        candidate.relative_to(FRONTEND_DIR.resolve())
    except ValueError:
        return FileResponse(FRONTEND_DIR / "index.html")
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIR / "index.html")


def open_browser() -> None:
    webbrowser.open("http://127.0.0.1:5173", new=1)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    threading.Timer(1.2, open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=5173, log_level="warning")
