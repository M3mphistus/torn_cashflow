# Torn Cashflow Dashboard

A shared KPI dashboard for [Torn.com](https://www.torn.com), built with Streamlit and a
hosted Postgres database. Tracks cashflow, energy/nerve usage, and networth from your own
Torn API data, plus a recurring checklist. Every visitor pastes their own Torn API key —
your data is scoped to your Torn player ID and never visible to anyone else.

## Setup (local development)

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml` (gitignored, never commit it) with:

```toml
DATABASE_URL = "postgresql://user:password@host:5432/dbname?sslmode=require"
DEV_TORN_PLAYER_ID = 1234567   # the developer's own Torn player id — where Premium payments go
XANAX_ITEM_ID = 206             # Torn's item id for Xanax
```

`DATABASE_URL` needs a real Postgres instance — a free [Supabase](https://supabase.com) or
[Neon](https://neon.tech) project both work. Use the **pooled/transaction-mode** connection
string, not the direct one, since this app connects fresh per request.

Then run:

```bash
streamlit run Home.py
```

The app creates all tables automatically on first run.

## Getting a Torn API key

1. Log in to [torn.com](https://www.torn.com).
2. Go to **Settings** → **API**.
3. Create a new key with **Full Access**.
4. In this app, open **Settings** and paste the key in. It's kept only in your browser
   session (never written to disk or shared) — you'll re-paste it each time you visit.

## How syncing works

Nothing is fetched automatically. Go to **Sync** and click **Sync now** whenever you want
fresh data. Each sync pulls your current bars, money, and personal stats, stores a
snapshot, and fetches log entries since the last sync for cashflow categorization.
Uncategorized log entries can be tagged manually on the same page, or in bulk on the
**Categories** page.

## Free vs. Premium

| | Free | Premium |
|---|---|---|
| Manual "Sync now" | ✅ | ✅ |
| Dashboard (KPIs, charts, networth) | ✅ | ✅ |
| Checklist (manual add/edit/check-off) | ✅ | ✅ |
| Checklist auto-reset of recurring tasks | — | ✅ |
| "Get all Data" (full history sync) | — | ✅ |
| Categories page (custom categories, bulk recategorize) | — | ✅ |

Premium unlocks for 4 weeks by sending **1 Xanax** in-game to the developer's Torn account
(shown on the **Settings** page), detected automatically — no manual approval needed. A
faction can also buy one shared license for the whole faction at a bulk discount that
scales with member count. Every Torn player also gets a one-time **7-day free trial**.

## Notes on accuracy

Torn's API does not expose a running "lifetime energy/nerve spent" counter — only the
current bar value. Since this app only syncs on demand (no background polling), any
energy/nerve KPIs derived from bar deltas are only accurate across short gaps between
syncs, since regeneration between syncs hides some of the real spend.

## Project layout

- `Home.py` — entrypoint and landing page
- `auth.py` — session-scoped API key + Torn identity resolution
- `licensing.py` — Free/Premium status, trial, and Xanax payment detection
- `torn_api.py` — Torn API client
- `db.py` — Postgres schema and CRUD (tenant-scoped by Torn player id)
- `calculations.py` — KPI math and log categorization
- `pages/` — Dashboard, Sync, Checklist, Settings, Categories
- `theme.py` / `speakeasy.css` / `.streamlit/config.toml` — the app's visual theme
