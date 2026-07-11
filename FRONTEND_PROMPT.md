# Frontend build prompt — Torn Cashflow React rewrite

You are building the frontend for a rewrite of an existing, working Streamlit app into a proper
React frontend + Python backend. You are one of two independent AI sessions working on this —
a separate session is building the FastAPI backend from `BACKEND_PROMPT.md` in parallel, with
no visibility into your session or vice versa. **`API_CONTRACT.md` (repo root) is the exact,
binding contract the backend implements — endpoint paths, request/response JSON shapes, casing
(`camelCase`), timestamp format (unix seconds), and error shape are not negotiable, since the
backend is being built against that document verbatim.** Read it in full before writing any
code — every API call you make must match it exactly.

## Why this rewrite is happening

The existing Streamlit app (still present at the repo root — `Home.py`, `pages/`, `theme.py`,
`speakeasy.css`, etc. — reference these for exact current behavior, but don't modify them) hit
real platform limits: Streamlit Community Cloud's proxy strips almost all cookies before they
reach the app process, page reloads took 6-10 seconds even with caching, and Streamlit gave
little control over layout. The owner decided to stop patching Streamlit and rewrite as React +
Python, hosted on Render.com's free tier. This is a chance to give the user actual control over
layout/UX that Streamlit never allowed — don't just mechanically clone six Streamlit pages, feel
free to make reasonable UX improvements as long as every feature below is still present and
every API interaction matches `API_CONTRACT.md`.

## Stack

React + TypeScript + Vite, deployed as a Render "Static Site" from a `/frontend` subdirectory of
this same repo. Router: your choice (React Router is the standard pick). State/data-fetching:
your choice (TanStack Query pairs well with a polling-based job-status endpoint like full-history
sync, but plain `fetch` + hooks is fine too for a project this size — don't over-engineer).

## Auth flow

- On app load, call `GET /api/auth/me`. `200` → logged in, render the app with that player's
  data. `401` → show a login view (paste-your-API-key form) instead of the dashboard.
- **Every single `fetch()` call to the backend must set `credentials: 'include'` explicitly.**
  This is required for the cross-site session cookie (frontend and backend are different Render
  subdomains) and is the single easiest thing to silently break — write one shared API-client
  wrapper function that every call goes through, rather than calling `fetch` ad hoc from
  components, so this can't be forgotten in some call sites and not others.
- Login form posts the pasted key to `POST /api/auth/login`. On success, the backend sets the
  session cookie automatically (nothing to store client-side) — just refetch `/api/auth/me` (or
  use the login response directly, which returns the same `player`/`premium` shape) and switch
  to the logged-in view.
- "Log out" button calls `POST /api/auth/logout`, then returns to the login view.
- The **API key creation link** shown to a new user must deep-link to Torn's own key-builder
  with the app's exact required scopes pre-checked, exactly as the old app did:
  ```
  https://www.torn.com/preferences.php#tab=api?step=addNewKey&title=Torn%20Cashflow%20Dashboard&user=basic,profile,bars,money,personalstats,log
  ```
  Explain briefly why (read-only, scoped key — no blanket Full Access needed) — see the old
  Settings page's copy in `pages/4_Settings.py` for tone/wording to reuse or adapt.
- **Known risk, not something to solve upfront**: Safari and Chrome's evolving third-party-
  cookie restrictions can affect cross-site cookies like this one even with `SameSite=None;
  Secure` set correctly. If login appears to work but the session doesn't persist across
  reloads specifically in Safari, that's the likely cause — flag it back to the user rather than
  spending a long time debugging blind, since the real fix (same-domain deployment via a custom
  domain) is a deployment change, not a frontend code change.

## Cold-start UX

Render's free-tier backend spins down after ~15 minutes idle; the first request after that can
take 30-60 seconds. Show a clear "waking up the server…" loading state (not a bare spinner that
looks hung) for the initial `/api/auth/me` call specifically, since that's the one guaranteed to
fire on every fresh page load.

## Visual identity — "Speakeasy Ledger"

Port the existing theme's spirit into real, reusable React components/CSS rather than the old
`[data-testid]`-override hacks (those existed only because Streamlit doesn't expose real
component APIs — you don't have that constraint). Reference `speakeasy.css` (repo root) for the
complete existing rule set; the essentials:

- **Palette**: `--gold: #c9a227` (primary accent), `--gold-bright: #e4c258` (highlights/big
  numbers), `--gold-deep: #8a6d1a`, `--canvas: #14100b` (page background), `--panel: #1d1710` /
  `--panel-2: #181209` (card backgrounds), `--ink: #0a0806` (deepest black, used for inputs),
  `--text: #e8dfc9` (champagne body text), `--text-mute: #9a8e74`, `--text-dim: #928468`
  (WCAG AA-verified against canvas/panel-2 — don't go lighter/dimmer than this without
  re-checking contrast), `--green: #7f9a5b` (positive cashflow), `--red: #a33a2e` (negative).
- **Fonts**: Cinzel (headings — serif, art-deco feel), Oswald (labels/uppercase/buttons —
  condensed sans), Archivo (body text). Self-host these (the old app used woff2 files under
  `static/fonts/` referenced from `.streamlit/config.toml`'s `[[theme.fontFaces]]`) rather than
  a render-blocking web-font `<link>`.
- **Motifs worth carrying over**: square corners (no border-radius anywhere), thin gold
  hairline borders/dividers, small gold diamond bullet before `h3`-level subheadings, deco
  corner-bracket accents on KPI/metric cards, uppercase-letterspaced button/label text, a
  left-gold-border style for alert/banner boxes, a "Premium" badge (small bordered pill, gold
  text) shown inline next to gated feature headings.
- Dark theme only — there's no light-mode variant in the current app and no need to add one.

## Pages / features to build

Reuse `API_CONTRACT.md` for exact request/response shapes for everything below.

### Login / landing (no equivalent Streamlit page — new)
API key paste form when logged out. See Auth flow above.

### Home
Status summary: signed-in player name + faction, Premium status banner (with an expiry warning
if `isExpiringSoon`), last-synced timestamp, nav cards to the other pages, a note that free tier
covers day-to-day tracking while Premium (full history sync, Categories, auto checklist resets)
unlocks via 7-day trial or Xanax payment. Footer: link to the GitHub repo, a data/privacy note,
and a feedback line linking to the developer's Torn profile — reuse copy from `Home.py`.

### Dashboard
Time-range selector (`Last 7 days` / `Last 30 days` / `Last 90 days` / `Custom` date-range /
`All time`) that resolves to `startTs`/`endTs` and calls `GET /api/dashboard`. Render:
- Two KPI cards: Total Cashflow, Cashflow/Day
- Cashflow-by-category horizontal bar chart (gold for positive, red/oxblood for negative — see
  `--green`/`--red`... actually old app used gold/red for the bars specifically, green is used
  elsewhere; check `pages/1_Dashboard.py`'s `apply_chart_theme`/color mapping if you want the
  exact original palette)
- Networth breakdown table (all rows from `networthBreakdown`, including the always-null "Trade"
  row shown as "n/a" — with a caption noting this reflects Torn's own once-daily-computed
  networth figure, not a live estimate)
- Daily time-series, tabbed: Cashflow/Day (bar chart) and Networth (line chart)
- Raw snapshot table + CSV export button (client-side CSV generation from `snapshots` is fine —
  no new backend endpoint needed for this)
Use any charting library you like (Recharts, Chart.js, Visx, etc.) — Plotly isn't required, the
old app only used it because it was the easy Streamlit-native option.

### Sync
"Sync now" button → `POST /api/sync/incremental`, show a success message with entries-stored
count and any `paymentMessage`. "Get all Data" (Premium-gated, show an upsell message if not
Premium rather than hiding the button entirely) → `POST /api/sync/full-history`, then poll
`GET /api/sync/full-history/{jobId}` every ~2-3s showing live progress (page count, entries
fetched, oldest timestamp reached) until `completed`/`failed`. Period note editor for the latest
snapshot. Uncategorized-entries review list (title, timestamp, amount-or-"no amount detected",
raw text, category dropdown + note field + Save/Ignore buttons per entry) capped at 25 with a
"showing X of Y" note pointing to the Categories page for bulk work. Collapsed "Ignored entries"
section with per-entry Restore buttons. Danger Zone: `DELETE /api/data` gated behind an explicit
confirmation checkbox before the button is enabled — this is irreversible, don't let a single
accidental click trigger it.

### Checklist
Add-task form (title, optional description, repeat type dropdown, conditional "every X days"
number input). Open tasks grouped by repeat type, each with a Done checkbox, Edit (inline form),
Delete. Completed tasks in a collapsed section, can be un-done from there. War Mode toggle
lives on Settings, not here, but `war_day`-type tasks should only render when War Mode is
currently active (check via `GET /api/settings/war-mode`). Free-tier users see a note that they
must manually re-open completed recurring tasks; Premium users get server-side auto-reset
transparently (nothing extra to build client-side for that — `GET /api/checklist` already
reflects post-reset state for Premium accounts).

### Settings
API key entry/re-entry form, masked-key display, Log out. War Mode toggle with explanatory
caption. Premium/License status section: current status + expiry warning, "Start my 7-day free
trial" button (hidden once used or already Premium), pay-for-Premium section with a toggle
between "just myself" and (if in a faction) "my whole faction" — faction mode shows the bulk
discount preview (`GET /api/licensing/faction-preview`) before the "Check my payment now"
button (`POST /api/licensing/scan-payment` or `scan-group-payment` depending on mode). Admin
panel (only rendered if `player.isAdmin` from the auth response) — grant/revoke lifetime Premium
by scope+ID, list current lifetime grants. Privacy/data-transparency section and feedback
section — reuse the copy from `pages/4_Settings.py`.

### Categories (Premium-gated — show upsell if not Premium)
Category list with entry counts, add-category form, delete button (disabled/tooltip when
`entryCount > 0`, since the backend rejects deletion of an in-use category anyway). Review &
Recategorize: a filterable, editable table of every log title with its current category and
entry count — inline category dropdown per row, an "Apply changes" button that diffs against
the original load and calls `POST /api/categories/reassign` for each changed row.

## Render deployment specifics

- **Root Directory**: `frontend`.
- **Build command**: `npm ci && npm run build` (Vite's default output is `dist/`).
- **Publish directory**: `dist`.
- Static Sites on Render don't spin down (no cold start for the frontend itself) — only the
  backend Web Service does. The dashboard shell will load instantly; only the first API call
  after backend idle is slow (see Cold-start UX above).
- **Environment variable**: `VITE_API_BASE_URL` — the backend's base URL (`http://localhost:8000`
  or similar for local dev against a locally-running backend, the deployed Render backend URL in
  production). Vite exposes `import.meta.env.VITE_API_BASE_URL` at build time.

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
`GIT_COMMITTER_DATE="<unix_epoch> -0700"`, using the current real timestamp — the offset is just
display metadata, the epoch itself should be the real time of the commit). Work on the
`rewrite-react` branch (already created off `dev`) — do not merge to `dev`/`main` yourself.

## Verification

Run locally with `npm run dev` against a running backend (local FastAPI instance or the deployed
Render backend, via `VITE_API_BASE_URL`). Walk through the full golden path: log in with a real
Torn API key → Sync now → Dashboard renders real charts → toggle War Mode → add/complete a
checklist task → (if Premium) run a full-history sync and watch progress poll → (if Premium)
add a category and reassign some entries → log out and confirm the login view reappears and
protected pages redirect to it. Check the browser console/network tab for any request missing
`credentials: 'include'` (shows up as the session cookie not being sent — `401`s on requests
that should be authenticated) and for any response field-name mismatch against
`API_CONTRACT.md`.
