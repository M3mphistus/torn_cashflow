# Torn Cashflow Dashboard

A shared KPI dashboard for [Torn.com](https://www.torn.com). Tracks cashflow, energy/nerve
usage, and networth from your own Torn API data, plus a recurring checklist. Every visitor
signs in with their own Torn API key — your data is scoped to your Torn player ID and never
visible to anyone else.

React (Vite + TypeScript) frontend, FastAPI backend, Postgres (Supabase) database.

## Project layout

- `backend/` — FastAPI app, Torn API client, Postgres schema/queries, Premium/licensing logic.
  See `backend/README.md` for local dev and deployment.
- `frontend/` — React app. See `frontend/README.md` for local dev (including a mock-backend
  mode for UI work without a live database) and deployment.
- `API_CONTRACT.md` — the REST contract between the two: endpoint shapes, auth cookie behavior,
  conventions (camelCase, unix timestamps, etc.). The reference when changing either side.

## Getting a Torn API key

This app never asks for a blanket Full Access key. Instead it uses Torn's **Custom** key type,
scoped to exactly the selections it reads: basic profile, bars, money, personalstats, and log.
The Settings page deep-links to Torn's own key creation page with exactly those selections
pre-checked, nothing more.

## How syncing works

Nothing is fetched automatically. Go to **Sync** and click **Sync now** whenever you want fresh
data. Each sync pulls current bars, money, and personal stats, stores a snapshot, and fetches
log entries since the last sync for cashflow categorization. Uncategorized log entries can be
tagged manually on the same page, or in bulk on the **Categories** page.

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
(shown on the **Settings** page), detected automatically — no manual approval needed. A faction
can also buy one shared license for the whole faction at a bulk discount that scales with member
count. Every Torn player also gets a one-time **7-day free trial**.

## Notes on accuracy

Torn's API does not expose a running "lifetime energy/nerve spent" counter — only the current
bar value. Since this app only syncs on demand (no background polling), any energy/nerve KPIs
derived from bar deltas are only accurate across short gaps between syncs, since regeneration
between syncs hides some of the real spend.
