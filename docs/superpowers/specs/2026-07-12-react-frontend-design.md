# Torn Cashflow React Frontend — Design

## Context

The Streamlit app (`Home.py`, `pages/`, repo root) is being rewritten as React + FastAPI on
Render.com, driven by two independent, non-communicating AI sessions built against
`API_CONTRACT.md` as the binding contract. The FastAPI backend (`/backend`) is already complete,
reviewed, and merged onto this branch. This spec covers the frontend half only, per
`FRONTEND_PROMPT.md` (repo root), which is treated as the authoritative feature list — this
document adds the architecture/implementation decisions that prompt intentionally left open
("your choice").

## Stack

Vite + React + TypeScript, deployed as a Render Static Site from `/frontend`.
- **Routing**: React Router v6.
- **Server state / data fetching**: TanStack Query.
- **Charts**: Recharts.

## API layer (`src/api/`)

- `client.ts` exports a single `apiFetch<T>(path, options)` wrapper: prefixes
  `import.meta.env.VITE_API_BASE_URL`, always sets `credentials: 'include'`, parses JSON, and on
  a non-2xx response parses the `{ error: { message, code, tornErrorCode } }` shape into a typed
  `ApiError` (fields: `message`, `code`, `tornErrorCode`, `status`) that callers can catch. No
  component or hook ever calls `fetch` directly — every request goes through this wrapper, so
  `credentials: 'include'` can't be silently dropped at some call site.
- One thin module per domain — `auth.ts`, `dashboard.ts`, `sync.ts`, `snapshots.ts`,
  `logEntries.ts`, `categories.ts`, `checklist.ts`, `settings.ts`, `licensing.ts`, `admin.ts`,
  `data.ts` — each exporting typed functions that call `apiFetch` and return typed DTOs. No
  business logic here beyond request shaping.
- `src/types/api.ts` mirrors every DTO in `API_CONTRACT.md` verbatim: camelCase fields, unix-
  second timestamps as `number`, `amount: number | null` never coerced to `0`.

## State management

TanStack Query owns all server state. A `useAuth()` hook wraps the `/api/auth/me` query and
exposes `{ player, premium, isAuthenticated, isLoading }` — read anywhere in the tree instead of
prop-drilling, and used to gate Premium-only UI (`premium.isPremium`) and the admin panel
(`player.isAdmin`). No separate global-state library (Redux/Zustand) — component-local state
covers forms, toggles, and multi-step UI (e.g. the Danger Zone confirmation checkbox).

Query key convention: `['dashboard', startTs, endTs]`, `['checklist']`, `['syncJob', jobId]`,
etc. — namespaced by domain, parameterized by whatever the request itself is parameterized by,
so range/filter changes naturally produce cache misses instead of stale data.

## Auth flow & routing shell

The app root runs the `/api/auth/me` query on mount. Three states:
1. **Loading** (first fire, cold backend) — a dedicated "waking up the server… this can take up
   to a minute after the app has been idle" panel, not a bare spinner.
2. **401** — render `LoginView` (API key paste form) only. No other route is reachable.
3. **200** — render the app shell (top bar with player name/Premium badge/logout, nav) with
   React Router routes for the six pages. No per-route guard components are needed since the
   entire shell already sits behind this gate; `LoginView` and the shell are mutually exclusive
   at the root, not per-route.

`POST /api/auth/login` success and `POST /api/auth/logout` both invalidate the `['auth','me']`
query rather than managing separate local "am I logged in" state, so the auth query stays the
single source of truth.

## Theming

`src/styles/theme.css` defines the CSS custom properties from `speakeasy.css` verbatim (`--gold`,
`--gold-bright`, `--gold-deep`, `--canvas`, `--panel`, `--panel-2`, `--ink`, `--text`,
`--text-mute`, `--text-dim`, `--green`, `--red`). Fonts (Cinzel, Oswald, Archivo) are copied from
`static/fonts/*.woff2` into `frontend/public/fonts/` and self-hosted via `@font-face` — no
render-blocking `<link>` to an external font host.

Reusable primitives in `src/components/ui/`: `Card`, `KpiCard` (deco corner-bracket accents),
`SectionHeading` (gold diamond bullet, used for every `h3`-level subheading), `AlertBanner`
(left-gold-border variant for info/warning), `PremiumBadge` (bordered gold pill), `Button`
(uppercase-letterspaced). Every page composes from these rather than re-implementing the motifs
inline. Square corners everywhere — no `border-radius` in the base styles.

## Pages

One file per page under `src/pages/`: `Login`, `Home`, `Dashboard`, `Sync`, `Checklist`,
`Settings`, `Categories` — each following `FRONTEND_PROMPT.md`'s feature list for that page
exactly. Dashboard's time-range presets resolve to concrete `startTs`/`endTs` client-side before
calling `GET /api/dashboard`. Sync's full-history job polls `GET /api/sync/full-history/{jobId}`
every 2-3s via TanStack Query's `refetchInterval`, stopping on `completed`/`failed`, with a
stalled-job affordance if there's no progress change for ~60s.

## Error handling

No global toast library. Inline `AlertBanner` per section for query/mutation errors, using the
`ApiError.message` text directly (already human-readable per the contract). A `401` from any
authenticated call *other than* the initial `/auth/me` bootstrap (i.e. a session that expired
mid-session) invalidates the auth query, which naturally drops the user back to `LoginView`.

## Dev-time verification (no live backend available in this worktree)

This worktree has no `.streamlit/secrets.toml` / `backend/.env` with real DB or Torn credentials,
so a live end-to-end run isn't possible here. `src/mocks/` will hold an MSW (Mock Service Worker)
setup implementing every `API_CONTRACT.md` endpoint with realistic fixture data, enabled only via
`VITE_USE_MOCKS=true` and excluded from the production build. This is a dev-only verification
tool, not a shipped feature — it lets the golden path (login → sync → dashboard → checklist →
settings → categories → logout) be clicked through in the browser preview before calling the
build done. A real end-to-end pass against the deployed backend is still needed once both sides
are live, per the contract's own Safari cross-site-cookie caveat.

## Build/deploy

`frontend/package.json` scripts: `dev`, `build`, `preview`, `lint`, `typecheck`. Render Static
Site: root `frontend`, build `npm ci && npm run build`, publish `dist`. Env var
`VITE_API_BASE_URL` (backend base URL, no trailing `/api`).

## Implementation task breakdown (for the plan)

1. Scaffold Vite+React+TS project, theme CSS + fonts, UI primitives.
2. API client + types + MSW mock setup.
3. Auth flow, routing shell, Login view.
4. Home page.
5. Dashboard page (charts, time-range selector, CSV export).
6. Sync page (incremental/full-history polling, uncategorized/ignored review, Danger Zone).
7. Checklist page.
8. Settings page (API key, War Mode, Premium/licensing, Admin panel).
9. Categories page.
10. Polish + full golden-path verification pass against mocks.
11. README + Render deploy config.

## Out of scope

Light-mode theme, offline/PWA support, i18n, any backend changes (backend is already complete
and frozen for this session), any Streamlit file changes.
