# Torn Cashflow — FastAPI backend

FastAPI port of the Streamlit app's backend logic, serving the React frontend per
`../API_CONTRACT.md`. See `../BACKEND_PROMPT.md` for the full design rationale.

## Local development

    cp .env.example .env   # fill in real values — see .streamlit/secrets.toml at the repo root
                            # for DATABASE_URL / DEV_TORN_PLAYER_ID / XANAX_ITEM_ID / DEV_TORN_PLAYER_NAME
    python -m venv .venv
    .venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip on macOS/Linux
    .venv/Scripts/uvicorn app.main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs

## Render deployment

- **Root Directory**: `backend`
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check path**: `/health`
- **Environment variables** (Render dashboard, production): `DATABASE_URL`, `DEV_TORN_PLAYER_ID`,
  `XANAX_ITEM_ID`, `DEV_TORN_PLAYER_NAME`, `JWT_SECRET`, `API_KEY_ENCRYPTION_SECRET`, `FRONTEND_ORIGIN`.

Free tier spins down after ~15 minutes idle; the next request pays a 30-60s cold start. This is an
accepted trade-off, not something to engineer around.
