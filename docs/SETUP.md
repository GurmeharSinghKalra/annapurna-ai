# Setup

## Requirements

- Python 3.13
- Node.js 20 or newer
- Docker and Docker Compose, for the container path only

Commands below are POSIX shell. On Windows PowerShell, activate the virtual environment with
`.venv\Scripts\Activate.ps1` and use `Copy-Item` in place of `cp`.

## Local development

```bash
git clone https://github.com/GurmeharSinghKalra/annapurna-ai.git
cd annapurna-ai
cp .env.example .env
```

Nothing in `.env` is required to start. Each key you add turns a labelled fallback into a real
data source; see the table in the main README.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Optional: build and train the crop model. The ranking works without it.
python scripts/build_dataset.py
python scripts/train_model.py

# Create the schema. Defaults to SQLite at backend/data/annapurna.db.
alembic upgrade head

uvicorn app.main:app --reload --port 8000
```

Check it: <http://127.0.0.1:8000/health> and <http://127.0.0.1:8000/docs>.

### Frontend

```bash
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The Vite dev server proxies `/api` to port 8000, so the browser
makes same-origin calls and development exercises the same code path as production.

Point the proxy somewhere else with `VITE_PROXY_TARGET`, or bypass it entirely with
`VITE_API_URL`.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, the API (which runs migrations on boot) and the frontend behind nginx.

- Frontend: <http://127.0.0.1:5174>
- API: <http://127.0.0.1:8000>

The frontend container resolves the backend at request time, so it starts and serves the app even
if the API is not up yet, returning a JSON 503 for API calls until it appears.

## PostgreSQL

Set `DATABASE_URL` to the provider's URL exactly as given. The libpq form is converted
automatically, including `?sslmode=require` and `channel_binding`, which `asyncpg` cannot parse:

```bash
DATABASE_URL=postgresql://user:password@host.neon.tech/dbname?sslmode=require
```

Then:

```bash
cd backend && alembic upgrade head
```

## Production

1. Set `APP_ENV=production`. The app then refuses to start without `JWT_SECRET` and will not
   create tables implicitly.
2. Generate a secret: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
3. Set `DATABASE_URL` to a managed PostgreSQL instance.
4. Set `CORS_ORIGINS` to your real frontend origin, and nothing else.
5. Run `alembic upgrade head` as a deploy step rather than relying on container start, if you run
   more than one API replica.
6. Terminate TLS in front of the frontend container.
7. Replace the in-process rate limiter with a shared one if you run more than one replica.
   `/health` reports which is in use.

### Health endpoints

| Endpoint | Use |
| --- | --- |
| `GET /health` | Liveness, plus which capabilities are actually configured |
| `GET /readyz` | Readiness. Returns 503 when the database is unreachable |

## Windows portable build

```powershell
cd distribution
.\build_windows_portable.ps1
```

Produces a folder containing an executable that serves the built frontend and the API from one
process, with SQLite data stored beside it. Create a `.env` in that folder to add API keys.
