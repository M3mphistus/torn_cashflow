# Torn Cashflow — React frontend

Vite + React + TypeScript frontend serving the FastAPI backend per `../API_CONTRACT.md`. See
`../FRONTEND_PROMPT.md` for the full design rationale and
`docs/superpowers/specs/2026-07-12-react-frontend-design.md` for the architecture decisions made
during the build.

## Local development

Against a real backend:

    cp .env.example .env   # set VITE_API_BASE_URL to your local/deployed backend URL
    npm install
    npm run dev

Against the built-in mocks (no backend/database/Torn API key needed):

    printf 'VITE_API_BASE_URL=\nVITE_USE_MOCKS=true\n' > .env
    npm install
    npm run dev

The mock server (`src/mocks/`) implements every `API_CONTRACT.md` endpoint with fixture data —
useful for UI work without standing up the backend. It's excluded from production builds.

## Checks

    npm run typecheck
    npm run lint
    npm run build
    npx vitest run

## Render deployment

- **Root Directory**: `frontend`
- **Build command**: `npm ci && npm run build`
- **Publish directory**: `dist`
- **Environment variable**: `VITE_API_BASE_URL` — the deployed backend's base URL (no trailing
  `/api`), e.g. `https://torn-cashflow-backend.onrender.com`.

Static Sites on Render don't spin down — only the backend Web Service does. The shell loads
instantly; only the first API call after backend idle is slow (the app shows a "waking up the
server…" state for that specific call).

## Known risk: Safari third-party cookies

The session cookie is cross-site (frontend and backend are different `*.onrender.com`
subdomains). Safari and Chrome's evolving third-party-cookie restrictions can affect this even
with `SameSite=None; Secure` set correctly. If login appears to work but the session doesn't
persist across reloads specifically in Safari, that's the likely cause — the real fix is
same-domain deployment via a custom domain, not a frontend code change.
