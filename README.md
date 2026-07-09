# Torn Cashflow Dashboard

Local KPI dashboard for [Torn.com](https://www.torn.com), built with Streamlit and SQLite. Tracks cashflow, energy/nerve usage, and networth from your own Torn API data, plus a recurring checklist. Everything runs and stores data locally — nothing leaves your machine except the direct API calls to Torn.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. On first run it creates `data/torn_dashboard.db` (SQLite) and seeds a few example checklist tasks.

## Getting a Torn API key

1. Log in to [torn.com](https://www.torn.com).
2. Go to **Settings** → **API**.
3. Create a new key with **Full Access**.
4. In this app, open the **Settings** page and paste the key in. It's saved locally to `config.json` (gitignored) and reloaded automatically on future launches.

## How syncing works

Nothing is fetched automatically. Go to the **Sync** page and click **Sync now** whenever you want fresh data. Each sync pulls your current bars, money, and personal stats, stores a snapshot, and fetches log entries since the last sync for cashflow categorization. Uncategorized log entries can be tagged manually on the same page.

## Notes on accuracy

Torn's API does not expose a running "lifetime energy/nerve spent" counter — only the current bar value. Since this app never polls in the background, the Energy/Nerve "spent (approx.)" KPIs are the raw bar-value drop between two syncs, which is only accurate if you sync at the start and end of an active play session (otherwise regeneration between syncs will hide some of the real spend). Exact refill counts (from Torn's personal stats) are shown alongside as a precise secondary signal.

## Project layout

- `app.py` — entrypoint and landing page
- `torn_api.py` — Torn API client
- `db.py` — SQLite schema and CRUD
- `calculations.py` — KPI math and log categorization
- `config.py` — local API key persistence
- `pages/` — Dashboard, Sync, Checklist, Settings
