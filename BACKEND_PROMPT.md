# Backend build prompt — Torn Cashflow FastAPI rewrite

You are building the backend for a rewrite of an existing, working Streamlit app into a proper
React frontend + Python backend. You are one of two independent AI sessions working on this —
a separate session is building the React frontend from `FRONTEND_PROMPT.md` in parallel, with
no visibility into your session or vice versa. **`API_CONTRACT.md` (repo root) is the exact,
binding contract you must implement — endpoint paths, request/response JSON shapes, casing
(`camelCase` at the HTTP boundary), timestamp format (unix seconds), and error shape are not
negotiable, since the frontend is being built against that document verbatim.** Read it in full
before writing any code.

## Why this rewrite is happening

The existing Streamlit app (still present at the repo root — `Home.py`, `pages/`, `auth.py`,
`db.py`, `torn_api.py`, `calculations.py`, `licensing.py`, `theme.py`, `speakeasy.css`) hit real
platform limits: Streamlit Community Cloud's proxy strips almost all cookies before they reach
the app process (confirmed by Streamlit's own staff), which broke a native cookie-read attempt
and forced a slower JS-component workaround; page reloads take 6-10 seconds even with caching;
and Streamlit gives little control over layout. The owner decided to stop patching Streamlit and
rewrite as React + Python, hosted on Render.com's free tier, keeping the existing Supabase
Postgres database and its data. **Do not touch the Streamlit files** — they stay as a working
fallback until this rewrite is verified and cut over.

## Stack & reuse

FastAPI, deployed as a Render "Web Service" from a `/backend` subdirectory of this same repo.
The business logic in the existing Streamlit modules is already implemented and bug-fixed this
session (e.g. a sign-flip bug on "Money send" entries, faction bulk-discount math) — **port it
into your backend largely as-is**, stripped of Streamlit-specific bits (`st.cache_data`,
`st.cache_resource`, `st.secrets`, `st.session_state`, any `st.*` UI calls) and wrapped in
FastAPI endpoints. Do not rewrite working, tested logic from scratch — read these files first:

- `db.py` (repo root) — every DB function you need, already written against the schema below
- `torn_api.py` (repo root) — the entire Torn API client (bars/money/personalstats/log/faction),
  error handling, and the log `amount` extraction logic (`_extract_amount`,
  `TITLE_AMOUNT_OVERRIDES`, `FORCE_NEGATIVE_TITLES`) — this has subtle, already-fixed edge cases,
  port it verbatim
- `calculations.py` (repo root) — cashflow/networth aggregation (pandas-based; keep pandas or
  reimplement with plain Python/dict aggregation, your call — the output shapes must match
  `API_CONTRACT.md`'s `GET /api/dashboard` regardless), auto-categorization keyword matching,
  checklist task-reset-due logic
- `licensing.py` (repo root) — the entire Premium paywall: Xanax-payment detection & crediting,
  trial, faction bulk-discount tiers, admin lifetime grants

## Database (Supabase Postgres — same instance, same data, minor additions)

Reuse the existing schema (from `db.py`'s `init_db()`) essentially verbatim:
`api_snapshots`, `log_entries`, `checklist_tasks`, `settings`, `category_rules`, `categories`,
`players`, `licenses`, `credited_payments`. Read `db.py` for the exact `CREATE TABLE` statements,
column names/types, and indices — reproduce them exactly (or via an ORM's migration if you
prefer SQLAlchemy/Alembic, but the resulting columns must match, since this is live production
data, not a fresh schema).

**New additions required for this rewrite:**

1. `players.api_key` (TEXT, nullable) — the backend now stores the Torn API key server-side
   after first login (old design kept it only in a browser cookie, re-sent every request; new
   design authenticates via a session cookie and looks up the stored key server-side when it
   needs to call Torn's API on the player's behalf). **Encrypt this at rest** using
   `cryptography.fernet` — generate a Fernet key once, store it as the `API_KEY_ENCRYPTION_SECRET`
   env var, encrypt before every `INSERT`/`UPDATE`, decrypt only at the point of use (building a
   Torn API call). Never return the raw key in any API response — only the masked form via the
   existing `mask_key()` logic in `auth.py`.
2. `players.key_invalidated_at` (BIGINT, nullable) — when a Torn API call using this player's
   stored key returns Torn error code `2` ("Incorrect API key"), set this to the current unix
   timestamp instead of clearing the key outright, and treat any session whose JWT predates this
   timestamp as invalid (forces re-login without needing a full session/blocklist table — a
   stateless JWT can't otherwise be revoked). Clear it back to `NULL` on the next successful
   login with a fresh key.
3. New table `sync_jobs` — required for the full-history sync background job (see below):
   ```sql
   CREATE TABLE IF NOT EXISTS sync_jobs (
       id BIGSERIAL PRIMARY KEY,
       torn_player_id BIGINT NOT NULL,
       status TEXT NOT NULL DEFAULT 'running',  -- 'running' | 'completed' | 'failed'
       pages_fetched INTEGER NOT NULL DEFAULT 0,
       entries_fetched INTEGER NOT NULL DEFAULT 0,
       oldest_timestamp BIGINT,
       error TEXT,
       new_entries_stored INTEGER,
       already_stored INTEGER,
       started_at BIGINT NOT NULL,
       finished_at BIGINT,
       updated_at BIGINT NOT NULL
   )
   ```

**Connection pool**: reuse `psycopg[binary,pool]` exactly as `db.py` does —
`ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=5, kwargs={"autocommit": True,
"row_factory": dict_row, "prepare_threshold": None})`. **`prepare_threshold=None` is required**
for Supabase's PgBouncer transaction-mode pooler — dropping it causes prepared-statement
protocol errors under load. Create the pool once at FastAPI startup (a `lifespan` context
manager), not per-request or via a decorator-based cache (there's no Streamlit session to scope
it to anymore — one pool for the process's lifetime is correct).

## Auth design

`POST /api/auth/login` validates the pasted key via `torn_api.get_basic_profile`, upserts
`players` (also clearing `key_invalidated_at`), encrypts+stores the key, and issues a JWT
(`{"playerId": ..., "issuedAt": ...}`, signed with `JWT_SECRET`, ~400-day expiry) in an
`httpOnly; Secure; SameSite=None; Path=/` cookie named `session_token`. `SameSite=None` is
required (not just safer) because the frontend and backend are different Render subdomains —
`Lax`/`Strict` will silently break the cookie on cross-site requests. Every other authenticated
endpoint verifies this JWT, looks up the player, and additionally checks that
`key_invalidated_at` is either `NULL` or older than the token's `issuedAt` (see point 2 above).

Set up CORS (`fastapi.middleware.cors.CORSMiddleware`) with `allow_credentials=True` and an
explicit origin allow-list containing the deployed frontend's exact `https://*.onrender.com`
URL plus `http://localhost:5173` (Vite's default dev port) for local development — a wildcard
origin does not work with `allow_credentials=True` per the CORS spec, so this must be an exact
list, not `*`.

## Full-history sync — must be async, not synchronous

`torn_api.get_full_log()` can page up to 200 times with a 0.7s delay between pages
(~140s worst case). **Render's free-tier Web Service has a ~30 second request timeout — a
synchronous endpoint doing this will always fail for any account with meaningful history.**
Implement `POST /api/sync/full-history` using FastAPI's `BackgroundTasks`:

1. Insert a `sync_jobs` row (`status='running'`), return `{"jobId": ..., "status": "running"}`
   immediately (`202`).
2. The background task runs `get_full_log`-equivalent paging logic, but **checkpoints progress
   into `sync_jobs` after every single page** (not just at the end) — update `pages_fetched`,
   `entries_fetched`, `oldest_timestamp`, `updated_at` each iteration. This matters because a
   free-tier dyno can restart mid-job; checkpointing means a stalled job is at least visible/
   diagnosable rather than silently losing all progress with no trace.
3. On completion, insert the new log entries (same dedup-by-`torn_log_id` + auto-categorize
   pipeline as incremental sync), set `status='completed'`, `finished_at`, `new_entries_stored`,
   `already_stored`.
4. On any exception, set `status='failed'`, `error=<message>`, `finished_at`.
5. `GET /api/sync/full-history/{jobId}` just reads the row back per `API_CONTRACT.md`'s shape.

## Render deployment specifics

- **Root Directory**: `backend` (set explicitly in the Render dashboard — don't rely on
  auto-detection, since the repo root also has a Streamlit `requirements.txt` that must not be
  picked up instead).
- **Build command**: `pip install -r requirements.txt`.
- **Start command**: bind to `0.0.0.0:$PORT` — Render sets `$PORT` dynamically per deploy;
  never hardcode a port. E.g. `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (adjust the
  module path to wherever your FastAPI `app` instance actually lives).
- **Health check**: implement `GET /health` returning `200 "ok"` with zero DB/Torn-API calls,
  and set it as the Render health check path — a health check that touches a possibly-slow
  dependency causes spurious restarts.
- **Cold starts**: free tier spins the service down after ~15 minutes idle; the next request
  pays a ~30-60s cold-start cost. This is an accepted trade-off of free tier, not something to
  engineer around — just make sure the health-check endpoint above doesn't make it worse.
- **Required environment variables** (Render dashboard env vars in production; a gitignored
  `.env` file loaded via `pydantic-settings` or `python-dotenv` locally):
  - `DATABASE_URL` — Supabase Postgres connection string (same value the Streamlit app uses,
    found in its `.streamlit/secrets.toml`, not committed)
  - `DEV_TORN_PLAYER_ID`, `XANAX_ITEM_ID`, `DEV_TORN_PLAYER_NAME` — same values as the existing
    `licensing.py` secrets
  - `JWT_SECRET` — new, generate a long random value
  - `API_KEY_ENCRYPTION_SECRET` — new, a Fernet key (`Fernet.generate_key()`)
  - `FRONTEND_ORIGIN` — the deployed frontend's URL, for the CORS allow-list

## Git commits

This repo's entire history uses a single consistent identity. Set these env vars before every
commit you make (do not use `git commit` without them — a bare commit will pick up whatever
local git config happens to be active and break the convention):
```
GIT_AUTHOR_NAME="M3mphistus"
GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com"
GIT_COMMITTER_NAME="M3mphistus"
GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com"
```
Commit dates should use a `-0700` timezone offset (e.g. `GIT_AUTHOR_DATE="<unix_epoch> -0700"`,
`GIT_COMMITTER_DATE="<unix_epoch> -0700"`, using the current real timestamp — the offset is
just display metadata, the epoch itself should be the real time of the commit). Work on the
`rewrite-react` branch (already created off `dev`) — do not merge to `dev`/`main` yourself.

## Verification

Run locally with `uvicorn` and exercise every endpoint via FastAPI's automatic `/docs` (Swagger
UI) — confirm request/response shapes match `API_CONTRACT.md` exactly, including camelCase keys
and null-vs-zero `amount` handling. Test against the real Supabase database (same `DATABASE_URL`
the Streamlit app already uses) so you're validating against real production data, not a fresh
empty schema. Specifically verify: login with a real Torn API key works end-to-end; incremental
sync stores a snapshot and log entries; the dashboard aggregate endpoint's numbers match what
the existing Streamlit Dashboard page shows for the same player/date range (cross-check against
the live app if unsure); full-history sync's background job actually completes and is pollable;
Premium gating returns `403` correctly for a non-Premium account on `/api/sync/full-history`.
