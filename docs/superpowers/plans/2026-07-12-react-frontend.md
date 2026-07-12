# Torn Cashflow React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/frontend` React + TypeScript app (Vite) that implements every page/feature in `FRONTEND_PROMPT.md` against `API_CONTRACT.md`, ported from the reference Streamlit app.

**Architecture:** Vite + React + TypeScript. React Router v6 for routing. TanStack Query owns all server state (including full-history-sync job polling). Recharts for charts. A single `apiFetch` wrapper (always `credentials: 'include'`) backs every domain-specific API module. A single `theme.css` ports the "Speakeasy Ledger" tokens/motifs from `speakeasy.css` onto real React components (no `[data-testid]` hacks needed). Dev-only MSW mocks (`VITE_USE_MOCKS=true`) stand in for the live backend so the golden path can be verified in-browser without real DB/Torn credentials.

**Tech Stack:** React 18, TypeScript, Vite, react-router-dom v6, @tanstack/react-query v5, recharts, msw (dev-only), vitest + jsdom (unit tests for pure logic only — see Global Constraints).

## Global Constraints

- **Git identity for every commit in this plan:**
  `GIT_AUTHOR_NAME="M3mphistus"`, `GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com"`,
  `GIT_COMMITTER_NAME="M3mphistus"`, `GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com"`.
  Set all four env vars on every `git commit` invocation — never a bare `git commit`. Use
  `GIT_AUTHOR_DATE="$(date +%s) -0700"` / `GIT_COMMITTER_DATE="$(date +%s) -0700"` (real current epoch, `-0700` display offset).
- **Branch:** work stays on the current branch (`claude/torn-cashflow-react-frontend-8e7502`, a worktree branch). Do not merge to `dev`/`main`/`rewrite-react` yourself.
- **Every `fetch()` call must go through `src/api/client.ts`'s `apiFetch`.** No component or hook calls `fetch` directly. This is the single easiest requirement to accidentally violate — grep for raw `fetch(` outside `src/api/client.ts` and `src/mocks/` before considering any task done.
- **JSON field casing**: all types in `src/types/api.ts` are camelCase, matching `API_CONTRACT.md` exactly. Never invent a field name — if unsure, re-check `API_CONTRACT.md` (repo root).
- **Timestamps** are unix seconds (`number`), never `Date` objects or ISO strings, at the API boundary. Convert to `Date` only inside formatting helpers (`src/lib/format.ts`).
- **No `border-radius` anywhere** in `theme.css` or inline styles — square corners is a deliberate motif.
- **Testing strategy** (do not deviate without re-reading this): this app has two kinds of code —
  (a) pure logic (`src/api/client.ts`'s error parsing, `src/lib/dateRange.ts`, `src/lib/csv.ts`,
  `src/lib/format.ts`) gets real TDD with Vitest — write the failing test first, per the steps below.
  (b) React components/pages are verified by `npm run typecheck`, `npm run build`, `npm run lint`,
  and manual click-through in the browser preview against the MSW mocks (Task 6 onward) — this
  matches the approved design spec (`docs/superpowers/specs/2026-07-12-react-frontend-design.md`),
  which explicitly chose browser-based golden-path verification over a component test suite. Do not
  add a component-testing library (React Testing Library etc.) — out of scope per that spec.
- **Assumption flagged for the user**: the developer's Torn profile (used in "send Torn message to
  ___" / "send 1 Xanax to ___" copy) isn't exposed by any API endpoint — it's backend-only config
  (`backend/.env.example`'s `DEV_TORN_PLAYER_ID=4316364`, `DEV_TORN_PLAYER_NAME="the developer"`).
  Task 7 hardcodes these same values as a frontend constant (`src/constants.ts`) since that's the
  only source of truth available in this repo. If the real developer name differs from the literal
  string `"the developer"`, that's a one-line fix in `src/constants.ts` — flag this to the user
  after Task 7, don't block on it.

---

## File Structure

```
frontend/
  package.json, vite.config.ts, tsconfig.json, tsconfig.node.json, index.html
  .env.example, .gitignore, eslint.config.js
  public/fonts/{Cinzel-Variable.woff2, Oswald-Variable.woff2, Archivo-Variable.woff2}
  src/
    main.tsx, App.tsx, constants.ts
    styles/theme.css
    types/api.ts
    api/client.ts, client.test.ts
    api/{auth,dashboard,snapshots,logEntries,sync,categories,checklist,settings,licensing,admin,data}.ts
    api/dashboard.test.ts, api/snapshots.test.ts
    lib/{format,dateRange,csv}.ts + matching .test.ts files
    hooks/useAuth.ts
    components/ui/{Card,KpiCard,SectionHeading,AlertBanner,PremiumBadge,Button}.tsx
    components/layout/{AppShell,NavCard}.tsx
    components/loading/ColdStartLoader.tsx
    pages/{Login,Home,Dashboard,Sync,Checklist,Settings,Categories}.tsx
    mocks/{data,handlers,browser}.ts
  backend README already exists at ../backend/README.md — this task only adds frontend/README.md
```

---

### Task 1: Scaffold Vite project, theme CSS, fonts

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/index.html`, `frontend/eslint.config.js`, `frontend/.gitignore`, `frontend/.env.example`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles/theme.css`
- Copy: `static/fonts/Cinzel-Variable.woff2` → `frontend/public/fonts/Cinzel-Variable.woff2` (and `Oswald-Variable.woff2`, `Archivo-Variable.woff2`)

**Interfaces:**
- Produces: the CSS custom properties (`--gold`, `--gold-bright`, `--gold-deep`, `--canvas`, `--panel`, `--panel-2`, `--ink`, `--text`, `--text-mute`, `--text-dim`, `--green`, `--red`, `--line`, `--line-lit`) and font-family tokens (`--head`, `--label`, `--body`) that every later task's components rely on. Also produces base classes: `.page`, `.eyebrow`, `.nav-grid`, `.page-footer` used by Task 8+.

- [ ] **Step 1: Copy the font files**

```bash
mkdir -p frontend/public/fonts
cp static/fonts/Cinzel-Variable.woff2 frontend/public/fonts/
cp static/fonts/Oswald-Variable.woff2 frontend/public/fonts/
cp static/fonts/Archivo-Variable.woff2 frontend/public/fonts/
```

- [ ] **Step 2: Write `frontend/package.json`**

```json
{
  "name": "torn-cashflow-frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "typecheck": "tsc -b --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "recharts": "^2.13.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.11",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.2",
    "eslint": "^9.12.0",
    "@eslint/js": "^9.12.0",
    "typescript-eslint": "^8.8.1",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.13",
    "globals": "^15.10.0",
    "jsdom": "^25.0.1",
    "msw": "^2.4.11",
    "typescript": "^5.6.3",
    "vite": "^5.4.8",
    "vitest": "^2.1.2"
  }
}
```

- [ ] **Step 3: Write `frontend/tsconfig.json` and `frontend/tsconfig.node.json`**

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vite/client"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Write `frontend/vite.config.ts`**

```typescript
/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: false,
  },
});
```

- [ ] **Step 5: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Torn Cashflow Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write `frontend/.gitignore` and `frontend/.env.example`**

`frontend/.gitignore`:
```
node_modules
dist
.env
```

`frontend/.env.example`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCKS=false
```

- [ ] **Step 7: Write `frontend/eslint.config.js`**

```javascript
import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    },
  },
);
```

- [ ] **Step 8: Write `frontend/src/styles/theme.css`**

```css
@font-face {
  font-family: 'Cinzel';
  src: url('/fonts/Cinzel-Variable.woff2') format('woff2');
  font-weight: 400 900;
  font-display: swap;
}
@font-face {
  font-family: 'Oswald';
  src: url('/fonts/Oswald-Variable.woff2') format('woff2');
  font-weight: 200 700;
  font-display: swap;
}
@font-face {
  font-family: 'Archivo';
  src: url('/fonts/Archivo-Variable.woff2') format('woff2');
  font-weight: 100 900;
  font-display: swap;
}

:root {
  --ink: #0a0806;
  --canvas: #14100b;
  --panel: #1d1710;
  --panel-2: #181209;
  --line: #2c2216;
  --line-lit: #3a2e1e;
  --gold: #c9a227;
  --gold-bright: #e4c258;
  --gold-deep: #8a6d1a;
  --text: #e8dfc9;
  --text-mute: #9a8e74;
  --text-dim: #928468;
  --green: #7f9a5b;
  --red: #a33a2e;
  --head: 'Cinzel', Georgia, serif;
  --label: 'Oswald', sans-serif;
  --body: 'Archivo', system-ui, sans-serif;
}

* { box-sizing: border-box; }

html, body, #root { height: 100%; }

body {
  margin: 0;
  background:
    radial-gradient(1200px 500px at 80% -10%, rgba(201, 162, 39, 0.06), transparent 60%),
    var(--canvas);
  color: var(--text);
  font-family: var(--body);
}

h1, h2, h3 {
  font-family: var(--head);
  color: var(--text);
  letter-spacing: 0.03em;
  font-weight: 700;
  margin: 0 0 0.6em;
}

h3 { display: flex; align-items: center; gap: 10px; }
h3::before {
  content: '';
  width: 7px;
  height: 7px;
  background: var(--gold);
  transform: rotate(45deg);
  flex-shrink: 0;
}

a { color: var(--gold); }
a:hover { color: var(--gold-bright); }

.eyebrow {
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 11px;
  color: var(--text-dim);
}

.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 20px 60px;
}

.page-footer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--gold);
  opacity: 0.9;
}
.page-footer p { color: var(--text-dim); font-size: 13px; }

hr, .divider {
  border: none;
  border-top: 1px solid var(--gold);
  opacity: 0.35;
  margin: 24px 0;
}

/* ---- Buttons ---- */
button, .btn {
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  border-radius: 0;
  border: 1px solid var(--line-lit);
  background: transparent;
  color: var(--gold);
  padding: 8px 16px;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
button:hover:not(:disabled), .btn:hover:not(:disabled) {
  background: rgba(201, 162, 39, 0.12);
  border-color: var(--gold);
  color: var(--gold-bright);
}
button:disabled, .btn:disabled { opacity: 0.4; cursor: not-allowed; }
button.primary, .btn.primary {
  background: var(--gold);
  color: var(--ink);
  border-color: var(--gold);
}
button.primary:hover:not(:disabled) { background: var(--gold-bright); }
button.danger { border-color: var(--red); color: var(--red); }
button.danger:hover:not(:disabled) { background: rgba(163, 58, 46, 0.15); color: var(--red); }

/* ---- Inputs ---- */
input, textarea, select {
  background: var(--ink);
  border: 1px solid var(--line-lit);
  border-radius: 0;
  color: var(--text);
  font-family: var(--body);
  padding: 8px 10px;
  width: 100%;
}
input:focus, textarea:focus, select:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 1px var(--gold);
}
label {
  display: block;
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 11px;
  color: var(--text-dim);
  margin-bottom: 4px;
}

/* ---- Card ---- */
.card {
  background: var(--panel-2);
  border: 1px solid var(--line);
  padding: 16px 18px;
}

/* ---- KPI card (deco corner brackets) ---- */
.kpi-card {
  background: linear-gradient(#1d1710, #161009);
  border: 1px solid var(--line-lit);
  padding: 16px 18px;
  position: relative;
}
.kpi-card::before, .kpi-card::after {
  content: '';
  position: absolute;
  top: 0; left: 0;
  background: var(--gold);
}
.kpi-card::before { width: 22px; height: 2px; }
.kpi-card::after { width: 2px; height: 22px; }
.kpi-label {
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 11px;
  color: var(--text-mute);
}
.kpi-value {
  font-family: var(--head);
  font-weight: 700;
  color: var(--gold-bright);
  font-size: 28px;
  margin-top: 6px;
}

/* ---- Alert banner (left gold border) ---- */
.alert-banner {
  border-left: 3px solid var(--gold);
  background: var(--panel-2);
  padding: 10px 14px;
  margin: 12px 0;
  font-family: var(--body);
}
.alert-banner.warning { border-left-color: var(--gold-bright); }
.alert-banner.error { border-left-color: var(--red); }
.alert-banner.success { border-left-color: var(--green); }

/* ---- Premium badge ---- */
.premium-badge {
  display: inline-block;
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 10px;
  padding: 2px 8px;
  margin-left: 10px;
  border: 1px solid var(--gold);
  color: var(--gold-bright);
  vertical-align: middle;
  white-space: nowrap;
}

/* ---- Nav grid (Home page) ---- */
.nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin: 24px 0;
}
.nav-card { text-decoration: none; display: block; color: inherit; }
.nav-card:hover { border-color: var(--gold); }
.nav-card .card { height: 100%; }

/* ---- App shell ---- */
.app-shell-top {
  border-bottom: 1px solid var(--line-lit);
  background: linear-gradient(#181209, #120d07);
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.app-shell-nav { display: flex; gap: 4px; flex-wrap: wrap; }
.app-shell-nav a {
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  padding: 6px 12px;
  color: var(--text-mute);
  text-decoration: none;
  border-bottom: 2px solid transparent;
}
.app-shell-nav a.active, .app-shell-nav a:hover { color: var(--gold-bright); border-bottom-color: var(--gold); }

/* ---- Tables ---- */
table { width: 100%; border-collapse: collapse; border: 1px solid var(--line); }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--line); }
th {
  background: var(--panel);
  font-family: var(--label);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 10px;
  color: var(--text-mute);
}
td { color: #cdbf9c; font-size: 13px; }

/* ---- Tabs ---- */
.tabs { display: flex; border-bottom: 1px solid var(--line-lit); gap: 2px; margin-bottom: 16px; }
.tabs button {
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  padding: 8px 14px;
}
.tabs button.active { color: var(--gold-bright); border-bottom-color: var(--gold); }
```

- [ ] **Step 9: Write a placeholder `frontend/src/App.tsx` and `frontend/src/main.tsx`**

`frontend/src/App.tsx`:
```tsx
export default function App() {
  return (
    <div className="page">
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Torn Cashflow Dashboard</h1>
    </div>
  );
}
```

`frontend/src/main.tsx`:
```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/theme.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 10: Install and verify**

```bash
cd frontend
npm install
npm run typecheck
npm run build
```
Expected: both commands exit 0.

- [ ] **Step 11: Commit**

```bash
cd frontend
git add package.json package-lock.json vite.config.ts tsconfig.json tsconfig.node.json index.html eslint.config.js .gitignore .env.example src/main.tsx src/App.tsx src/styles/theme.css public/fonts
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Scaffold Vite React frontend with Speakeasy Ledger theme"
```

---

### Task 2: UI primitives + format lib

**Files:**
- Create: `frontend/src/lib/format.ts`, `frontend/src/lib/format.test.ts`
- Create: `frontend/src/components/ui/Card.tsx`, `KpiCard.tsx`, `SectionHeading.tsx`, `AlertBanner.tsx`, `PremiumBadge.tsx`, `Button.tsx`

**Interfaces:**
- Consumes: CSS classes from Task 1's `theme.css` (`.card`, `.kpi-card`, `.kpi-label`, `.kpi-value`, `.alert-banner`, `.premium-badge`, `.btn`).
- Produces: `formatCurrency(amount: number | null): string`, `formatTimestamp(ts: number): string`,
  `formatDays(days: number): string` (used by Dashboard/Home/Settings in later tasks). Component
  exports: `Card`, `KpiCard`, `SectionHeading`, `AlertBanner`, `PremiumBadge`, `Button` (all default
  exports from their own file, named the same as the file).

- [ ] **Step 1: Write the failing test for `format.ts`**

`frontend/src/lib/format.test.ts`:
```typescript
import { describe, expect, it } from 'vitest';
import { formatCurrency, formatTimestamp, formatDays } from './format';

describe('formatCurrency', () => {
  it('formats a positive amount with thousands separators and no decimals', () => {
    expect(formatCurrency(1234567)).toBe('$1,234,567');
  });
  it('formats a negative amount', () => {
    expect(formatCurrency(-500)).toBe('-$500');
  });
  it('returns n/a for null', () => {
    expect(formatCurrency(null)).toBe('n/a');
  });
  it('rounds fractional amounts', () => {
    expect(formatCurrency(178571.4)).toBe('$178,571');
  });
});

describe('formatTimestamp', () => {
  it('formats a unix timestamp as UTC date + time', () => {
    expect(formatTimestamp(1730000000)).toBe('2024-10-27 02:53 UTC');
  });
});

describe('formatDays', () => {
  it('formats to one decimal place', () => {
    expect(formatDays(12.44)).toBe('12.4');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/format.test.ts`
Expected: FAIL — `./format` has no exported member (module doesn't exist yet).

- [ ] **Step 3: Write `frontend/src/lib/format.ts`**

```typescript
export function formatCurrency(amount: number | null): string {
  if (amount === null) return 'n/a';
  const rounded = Math.round(amount);
  const sign = rounded < 0 ? '-' : '';
  return `${sign}$${Math.abs(rounded).toLocaleString('en-US')}`;
}

export function formatTimestamp(ts: number): string {
  const iso = new Date(ts * 1000).toISOString();
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

export function formatDays(days: number): string {
  return days.toFixed(1);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/format.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Write the UI primitive components**

`frontend/src/components/ui/Card.tsx`:
```tsx
import type { ReactNode } from 'react';

export default function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`.trim()}>{children}</div>;
}
```

`frontend/src/components/ui/KpiCard.tsx`:
```tsx
export default function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}
```

`frontend/src/components/ui/SectionHeading.tsx`:
```tsx
import type { ReactNode } from 'react';
import PremiumBadge from './PremiumBadge';

export default function SectionHeading({ children, premium = false }: { children: ReactNode; premium?: boolean }) {
  return (
    <h3>
      {children}
      {premium && <PremiumBadge />}
    </h3>
  );
}
```

`frontend/src/components/ui/AlertBanner.tsx`:
```tsx
import type { ReactNode } from 'react';

type Kind = 'info' | 'success' | 'warning' | 'error';

export default function AlertBanner({ kind = 'info', children }: { kind?: Kind; children: ReactNode }) {
  return <div className={`alert-banner ${kind}`}>{children}</div>;
}
```

`frontend/src/components/ui/PremiumBadge.tsx`:
```tsx
export default function PremiumBadge() {
  return <span className="premium-badge">Premium</span>;
}
```

`frontend/src/components/ui/Button.tsx`:
```tsx
import type { ButtonHTMLAttributes } from 'react';

type Variant = 'default' | 'primary' | 'danger';

export default function Button({
  variant = 'default',
  className = '',
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const variantClass = variant === 'default' ? '' : variant;
  return <button className={`${variantClass} ${className}`.trim()} {...rest} />;
}
```

- [ ] **Step 6: Verify typecheck**

Run: `cd frontend && npm run typecheck`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
cd frontend
git add src/lib/format.ts src/lib/format.test.ts src/components/ui
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add format helpers and Speakeasy UI primitives"
```

---

### Task 3: API types + client wrapper

**Files:**
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`

**Interfaces:**
- Produces: every DTO type from `API_CONTRACT.md` (listed below), `ApiError` class (fields:
  `status: number`, `code: string`, `tornErrorCode: number | null`, `message` via `Error.message`),
  and `apiFetch<T>(path: string, options?: RequestInit): Promise<T>`. Every later API module task
  imports `apiFetch` and `ApiError` from `./client` and DTOs from `../types/api`.

- [ ] **Step 1: Write `frontend/src/types/api.ts`**

```typescript
export interface PlayerDTO {
  playerId: number;
  name: string | null;
  factionId: number | null;
  maskedApiKey: string;
  isAdmin: boolean;
}

export type PremiumSource = 'none' | 'trial' | 'individual' | 'faction' | 'lifetimeIndividual' | 'lifetimeFaction';

export interface PremiumStatusDTO {
  isPremium: boolean;
  premiumUntil: number | null;
  isLifetime: boolean;
  source: PremiumSource;
  isExpiringSoon: boolean;
  daysUntilExpiry: number | null;
}

export interface SessionDTO {
  player: PlayerDTO;
  premium: PremiumStatusDTO;
}

export interface SnapshotDTO {
  id: number;
  syncedAt: number;
  moneyOnhand: number;
  moneyPoints: number;
  vaultAmount: number;
  bankAmount: number;
  energyCurrent: number;
  energyMaximum: number;
  nerveCurrent: number;
  nerveMaximum: number;
  happyCurrent: number;
  happyMaximum: number;
  networth: number;
  nwPending: number;
  nwWallet: number;
  nwBank: number;
  nwPoints: number;
  nwCayman: number;
  nwVault: number;
  nwPiggybank: number;
  nwItems: number;
  nwDisplaycase: number;
  nwBazaar: number;
  nwItemmarket: number;
  nwProperties: number;
  nwStockmarket: number;
  nwAuctionhouse: number;
  nwCompany: number;
  nwBookie: number;
  nwEnlistedcars: number;
  nwLoan: number;
  nwUnpaidfees: number;
  refillsTotal: number;
  nerverefillsTotal: number;
  energydrinkusedTotal: number;
  xantakenTotal: number;
  warModeActive: boolean;
  note: string | null;
}

export interface CategoryBreakdownRow {
  category: string;
  amount: number;
}

export interface NetworthBreakdownRow {
  component: string;
  amount: number | null;
}

export interface DailyCashflowRow {
  date: string;
  cashflowDelta: number;
}

export interface DailyNetworthRow {
  date: string;
  networth: number;
}

export interface DashboardDTO {
  cashflowTotal: number;
  cashflowPerDay: number;
  categoryBreakdown: CategoryBreakdownRow[];
  networthBreakdown: NetworthBreakdownRow[];
  dailyCashflow: DailyCashflowRow[];
  dailyNetworth: DailyNetworthRow[];
  snapshots: SnapshotDTO[];
}

export interface LogEntryDTO {
  id: number;
  tornLogId: string;
  timestamp: number;
  category: string;
  title: string;
  rawText: string;
  amount: number | null;
  appCategory: string;
  userNote: string | null;
}

export interface CategoryDTO {
  name: string;
  entryCount: number;
}

export interface TitleSummaryRow {
  title: string;
  category: string;
  entryCount: number;
}

export type RepeatType = 'daily' | 'weekly' | 'every_x_days' | 'once' | 'war_day';

export interface ChecklistTaskDTO {
  id: number;
  title: string;
  description: string | null;
  repeatType: RepeatType;
  repeatIntervalDays: number | null;
  createdAt: number;
  lastCompletedAt: number | null;
  isDoneCurrentCycle: boolean;
}

export interface WarModeDTO {
  active: boolean;
  startedAt: number | null;
}

export interface LicensingStatusDTO extends PremiumStatusDTO {
  trialUsed: boolean;
}

export interface TrialResultDTO {
  started: boolean;
  reason: string | null;
  premiumUntil: number | null;
}

export interface ScanPaymentResultDTO {
  creditedCount: number;
  weeksAdded: number;
  newPremiumUntil: number | null;
  alreadyCreditedCount: number;
}

export interface FactionPreviewDTO {
  memberCount: number;
  lifetimeCoveredCount: number;
  payableMembers: number;
  discountPct: number;
  required: number;
}

export interface GroupScanResultDTO {
  activated: boolean;
  message: string;
  required: number | null;
  sent: number | null;
}

export type GrantScope = 'individual' | 'faction';

export interface LifetimeGrantDTO {
  scope: GrantScope;
  key: number;
  activatedAt: number;
}

export interface SyncIncrementalResultDTO {
  snapshot: SnapshotDTO;
  logEntriesStored: number;
  paymentMessage: string | null;
}

export interface FullHistoryJobStartDTO {
  jobId: number;
  status: 'running';
}

export type FullHistoryJobStatus = 'running' | 'completed' | 'failed';

export interface FullHistoryJobDTO {
  jobId: number;
  status: FullHistoryJobStatus;
  pagesFetched: number;
  entriesFetched: number;
  oldestTimestamp: number | null;
  error: string | null;
  result: { newEntriesStored: number; alreadyStored: number } | null;
}

export interface ApiErrorBody {
  message: string;
  code: string;
  tornErrorCode: number | null;
}
```

- [ ] **Step 2: Write the failing test for `client.ts`**

`frontend/src/api/client.test.ts`:
```typescript
import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, ApiError } from './client';

describe('apiFetch', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('always sends credentials: include', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/api/whatever');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.credentials).toBe('include');
  });

  it('returns parsed JSON on a 2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ hello: 'world' }), { status: 200 })),
    );

    const result = await apiFetch<{ hello: string }>('/api/whatever');
    expect(result).toEqual({ hello: 'world' });
  });

  it('returns undefined on a 204 response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })));

    const result = await apiFetch('/api/whatever');
    expect(result).toBeUndefined();
  });

  it('throws a typed ApiError parsed from the error envelope on non-2xx', async () => {
    const body = { error: { message: 'Incorrect API key.', code: 'invalid_key', tornErrorCode: 2 } };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status: 401 })));

    await expect(apiFetch('/api/auth/me')).rejects.toMatchObject({
      message: 'Incorrect API key.',
      code: 'invalid_key',
      tornErrorCode: 2,
      status: 401,
    });
    await expect(apiFetch('/api/auth/me')).rejects.toBeInstanceOf(ApiError);
  });

  it('defaults tornErrorCode to null when absent from the error envelope', async () => {
    const body = { error: { message: 'Category still in use.', code: 'category_in_use' } };
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status: 409 })));

    await expect(apiFetch('/api/categories/Job')).rejects.toMatchObject({ tornErrorCode: null });
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: FAIL — `./client` has no exported member `apiFetch`/`ApiError` (module doesn't exist yet).

- [ ] **Step 4: Write `frontend/src/api/client.ts`**

```typescript
import type { ApiErrorBody } from '../types/api';

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '';

export class ApiError extends Error {
  status: number;
  code: string;
  tornErrorCode: number | null;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.tornErrorCode = body.tornErrorCode ?? null;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const errorBody: ApiErrorBody = data?.error ?? {
      message: 'Something went wrong talking to the server.',
      code: 'unknown_error',
      tornErrorCode: null,
    };
    throw new ApiError(response.status, errorBody);
  }

  return data as T;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/client.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 6: Commit**

```bash
cd frontend
git add src/types/api.ts src/api/client.ts src/api/client.test.ts
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add API DTO types and the shared apiFetch client wrapper"
```

---

### Task 4: Domain API modules

**Files:**
- Create: `frontend/src/api/auth.ts`, `dashboard.ts`, `snapshots.ts`, `logEntries.ts`, `sync.ts`, `categories.ts`, `checklist.ts`, `settings.ts`, `licensing.ts`, `admin.ts`, `data.ts`
- Create: `frontend/src/api/dashboard.test.ts`, `frontend/src/api/snapshots.test.ts` (querystring-building is the only real logic here, worth testing; every other function is a one-line `apiFetch` pass-through already covered by Task 3's tests)

**Interfaces:**
- Consumes: `apiFetch`, `ApiError` from `./client`; all DTOs from `../types/api`.
- Produces (every later task imports these): `login(apiKey)`, `logout()`, `getMe()` from `auth.ts`;
  `getDashboard(startTs, endTs)` from `dashboard.ts`; `getSnapshots(startTs?, endTs?)`,
  `getLatestSnapshot()`, `updateSnapshotNote(id, note)` from `snapshots.ts`; `getLogEntries(params)`,
  `getUncategorizedEntries(limit?)`, `getIgnoredEntries(limit?)`, `updateLogEntry(id, appCategory, userNote?)`,
  `ignoreLogEntry(id, userNote?)`, `restoreLogEntry(id)`, `recategorizePeriod(startTs, endTs, appCategory)`
  from `logEntries.ts`; `syncIncremental()`, `startFullHistorySync()`, `getFullHistoryJob(jobId)` from
  `sync.ts`; `getCategories()`, `createCategory(name)`, `deleteCategory(name)`, `getTitleSummary(filterCategory?)`,
  `reassignCategory(title, fromCategory, toCategory)` from `categories.ts`; `getChecklist()`,
  `createTask(input: ChecklistTaskInput)`, `updateTask(id, input)`, `deleteTask(id)`, `setTaskDone(id, done)`
  and the `ChecklistTaskInput` interface from `checklist.ts`; `getWarMode()`, `setWarMode(active)` from
  `settings.ts`; `getLicensingStatus()`, `startTrial()`, `scanPayment(lookbackDays?)`,
  `getFactionPreview()`, `scanGroupPayment(lookbackDays?)` from `licensing.ts`; `getLifetimeGrants()`,
  `createLifetimeGrant(scope, key)`, `deleteLifetimeGrant(scope, key)` from `admin.ts`;
  `clearAllData()` from `data.ts`.

- [ ] **Step 1: Write `frontend/src/api/auth.ts`**

```typescript
import { apiFetch } from './client';
import type { SessionDTO } from '../types/api';

export function login(apiKey: string): Promise<SessionDTO> {
  return apiFetch<SessionDTO>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ apiKey }),
  });
}

export function logout(): Promise<void> {
  return apiFetch<void>('/api/auth/logout', { method: 'POST' });
}

export function getMe(): Promise<SessionDTO> {
  return apiFetch<SessionDTO>('/api/auth/me');
}
```

- [ ] **Step 2: Write the failing test for `dashboard.ts`'s querystring building**

`frontend/src/api/dashboard.test.ts`:
```typescript
import { describe, expect, it, vi } from 'vitest';
import * as client from './client';
import { getDashboard } from './dashboard';

describe('getDashboard', () => {
  it('calls /api/dashboard with startTs and endTs in the querystring', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({} as never);

    await getDashboard(1700000000, 1700600000);

    expect(spy).toHaveBeenCalledWith('/api/dashboard?startTs=1700000000&endTs=1700600000');
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/dashboard.test.ts`
Expected: FAIL — `./dashboard` module doesn't exist yet.

- [ ] **Step 4: Write `frontend/src/api/dashboard.ts`**

```typescript
import { apiFetch } from './client';
import type { DashboardDTO } from '../types/api';

export function getDashboard(startTs: number, endTs: number): Promise<DashboardDTO> {
  const params = new URLSearchParams({ startTs: String(startTs), endTs: String(endTs) });
  return apiFetch<DashboardDTO>(`/api/dashboard?${params.toString()}`);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/dashboard.test.ts`
Expected: PASS.

- [ ] **Step 6: Write the failing test for `snapshots.ts`'s optional querystring params**

`frontend/src/api/snapshots.test.ts`:
```typescript
import { describe, expect, it, vi } from 'vitest';
import * as client from './client';
import { getSnapshots, getLatestSnapshot, updateSnapshotNote } from './snapshots';

describe('getSnapshots', () => {
  it('omits the querystring entirely when no params are given', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshots: [] });
    await getSnapshots();
    expect(spy).toHaveBeenCalledWith('/api/snapshots');
  });

  it('includes only the params that were given', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshots: [] });
    await getSnapshots(1700000000);
    expect(spy).toHaveBeenCalledWith('/api/snapshots?startTs=1700000000');
  });

  it('includes both params when both are given', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshots: [] });
    await getSnapshots(1700000000, 1700600000);
    expect(spy).toHaveBeenCalledWith('/api/snapshots?startTs=1700000000&endTs=1700600000');
  });
});

describe('getLatestSnapshot', () => {
  it('calls the latest endpoint', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshot: null });
    await getLatestSnapshot();
    expect(spy).toHaveBeenCalledWith('/api/snapshots/latest');
  });
});

describe('updateSnapshotNote', () => {
  it('PATCHes the note as JSON', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ snapshot: {} as never });
    await updateSnapshotNote(501, 'War week 1');
    expect(spy).toHaveBeenCalledWith('/api/snapshots/501/note', {
      method: 'PATCH',
      body: JSON.stringify({ note: 'War week 1' }),
    });
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/api/snapshots.test.ts`
Expected: FAIL — `./snapshots` module doesn't exist yet.

- [ ] **Step 8: Write `frontend/src/api/snapshots.ts`**

```typescript
import { apiFetch } from './client';
import type { SnapshotDTO } from '../types/api';

export function getSnapshots(startTs?: number, endTs?: number): Promise<{ snapshots: SnapshotDTO[] }> {
  const params = new URLSearchParams();
  if (startTs !== undefined) params.set('startTs', String(startTs));
  if (endTs !== undefined) params.set('endTs', String(endTs));
  const qs = params.toString();
  return apiFetch<{ snapshots: SnapshotDTO[] }>(`/api/snapshots${qs ? `?${qs}` : ''}`);
}

export function getLatestSnapshot(): Promise<{ snapshot: SnapshotDTO | null }> {
  return apiFetch<{ snapshot: SnapshotDTO | null }>('/api/snapshots/latest');
}

export function updateSnapshotNote(id: number, note: string): Promise<{ snapshot: SnapshotDTO }> {
  return apiFetch<{ snapshot: SnapshotDTO }>(`/api/snapshots/${id}/note`, {
    method: 'PATCH',
    body: JSON.stringify({ note }),
  });
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/api/snapshots.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 10: Write the remaining domain modules (no dedicated tests — thin pass-throughs already covered by Task 3)**

`frontend/src/api/logEntries.ts`:
```typescript
import { apiFetch } from './client';
import type { LogEntryDTO } from '../types/api';

export function getLogEntries(params: { startTs?: number; endTs?: number; category?: string } = {}): Promise<{ entries: LogEntryDTO[] }> {
  const qs = new URLSearchParams();
  if (params.startTs !== undefined) qs.set('startTs', String(params.startTs));
  if (params.endTs !== undefined) qs.set('endTs', String(params.endTs));
  if (params.category) qs.set('category', params.category);
  const s = qs.toString();
  return apiFetch<{ entries: LogEntryDTO[] }>(`/api/log-entries${s ? `?${s}` : ''}`);
}

export function getUncategorizedEntries(limit = 25): Promise<{ entries: LogEntryDTO[]; totalCount: number }> {
  return apiFetch(`/api/log-entries/uncategorized?limit=${limit}`);
}

export function getIgnoredEntries(limit = 25): Promise<{ entries: LogEntryDTO[]; totalCount: number }> {
  return apiFetch(`/api/log-entries/ignored?limit=${limit}`);
}

export function updateLogEntry(
  id: number,
  appCategory: string,
  userNote?: string,
): Promise<{ entry: LogEntryDTO; bulkUpdatedCount: number }> {
  return apiFetch(`/api/log-entries/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ appCategory, userNote: userNote ?? null }),
  });
}

export function ignoreLogEntry(id: number, userNote?: string): Promise<{ entry: LogEntryDTO; bulkUpdatedCount: number }> {
  return apiFetch(`/api/log-entries/${id}/ignore`, {
    method: 'POST',
    body: JSON.stringify({ userNote: userNote ?? null }),
  });
}

export function restoreLogEntry(id: number): Promise<{ entry: LogEntryDTO }> {
  return apiFetch(`/api/log-entries/${id}/restore`, { method: 'POST' });
}

export function recategorizePeriod(startTs: number, endTs: number, appCategory: string): Promise<{ updatedCount: number }> {
  return apiFetch('/api/log-entries/recategorize-period', {
    method: 'POST',
    body: JSON.stringify({ startTs, endTs, appCategory }),
  });
}
```

`frontend/src/api/sync.ts`:
```typescript
import { apiFetch } from './client';
import type { FullHistoryJobDTO, FullHistoryJobStartDTO, SyncIncrementalResultDTO } from '../types/api';

export function syncIncremental(): Promise<SyncIncrementalResultDTO> {
  return apiFetch<SyncIncrementalResultDTO>('/api/sync/incremental', { method: 'POST' });
}

export function startFullHistorySync(): Promise<FullHistoryJobStartDTO> {
  return apiFetch<FullHistoryJobStartDTO>('/api/sync/full-history', { method: 'POST' });
}

export function getFullHistoryJob(jobId: number): Promise<FullHistoryJobDTO> {
  return apiFetch<FullHistoryJobDTO>(`/api/sync/full-history/${jobId}`);
}
```

`frontend/src/api/categories.ts`:
```typescript
import { apiFetch } from './client';
import type { CategoryDTO, TitleSummaryRow } from '../types/api';

export function getCategories(): Promise<{ categories: CategoryDTO[] }> {
  return apiFetch('/api/categories');
}

export function createCategory(name: string): Promise<{ name: string }> {
  return apiFetch('/api/categories', { method: 'POST', body: JSON.stringify({ name }) });
}

export function deleteCategory(name: string): Promise<void> {
  return apiFetch(`/api/categories/${encodeURIComponent(name)}`, { method: 'DELETE' });
}

export function getTitleSummary(filterCategory?: string): Promise<{ rows: TitleSummaryRow[] }> {
  const qs = filterCategory ? `?filterCategory=${encodeURIComponent(filterCategory)}` : '';
  return apiFetch(`/api/categories/title-summary${qs}`);
}

export function reassignCategory(title: string, fromCategory: string, toCategory: string): Promise<{ updatedCount: number }> {
  return apiFetch('/api/categories/reassign', {
    method: 'POST',
    body: JSON.stringify({ title, fromCategory, toCategory }),
  });
}
```

`frontend/src/api/checklist.ts`:
```typescript
import { apiFetch } from './client';
import type { ChecklistTaskDTO, RepeatType } from '../types/api';

export interface ChecklistTaskInput {
  title: string;
  description: string;
  repeatType: RepeatType;
  repeatIntervalDays: number | null;
}

export function getChecklist(): Promise<{ tasks: ChecklistTaskDTO[] }> {
  return apiFetch('/api/checklist');
}

export function createTask(input: ChecklistTaskInput): Promise<{ task: ChecklistTaskDTO }> {
  return apiFetch('/api/checklist', { method: 'POST', body: JSON.stringify(input) });
}

export function updateTask(id: number, input: ChecklistTaskInput): Promise<{ task: ChecklistTaskDTO }> {
  return apiFetch(`/api/checklist/${id}`, { method: 'PATCH', body: JSON.stringify(input) });
}

export function deleteTask(id: number): Promise<void> {
  return apiFetch(`/api/checklist/${id}`, { method: 'DELETE' });
}

export function setTaskDone(id: number, done: boolean): Promise<{ task: ChecklistTaskDTO }> {
  return apiFetch(`/api/checklist/${id}/done`, { method: 'POST', body: JSON.stringify({ done }) });
}
```

`frontend/src/api/settings.ts`:
```typescript
import { apiFetch } from './client';
import type { WarModeDTO } from '../types/api';

export function getWarMode(): Promise<WarModeDTO> {
  return apiFetch('/api/settings/war-mode');
}

export function setWarMode(active: boolean): Promise<WarModeDTO> {
  return apiFetch('/api/settings/war-mode', { method: 'PUT', body: JSON.stringify({ active }) });
}
```

`frontend/src/api/licensing.ts`:
```typescript
import { apiFetch } from './client';
import type {
  FactionPreviewDTO,
  GroupScanResultDTO,
  LicensingStatusDTO,
  ScanPaymentResultDTO,
  TrialResultDTO,
} from '../types/api';

export function getLicensingStatus(): Promise<LicensingStatusDTO> {
  return apiFetch('/api/licensing/status');
}

export function startTrial(): Promise<TrialResultDTO> {
  return apiFetch('/api/licensing/trial', { method: 'POST' });
}

export function scanPayment(lookbackDays = 7): Promise<ScanPaymentResultDTO> {
  return apiFetch('/api/licensing/scan-payment', {
    method: 'POST',
    body: JSON.stringify({ lookbackDays }),
  });
}

export function getFactionPreview(): Promise<FactionPreviewDTO | null> {
  return apiFetch('/api/licensing/faction-preview');
}

export function scanGroupPayment(lookbackDays = 7): Promise<GroupScanResultDTO> {
  return apiFetch('/api/licensing/scan-group-payment', {
    method: 'POST',
    body: JSON.stringify({ lookbackDays }),
  });
}
```

`frontend/src/api/admin.ts`:
```typescript
import { apiFetch } from './client';
import type { GrantScope, LifetimeGrantDTO } from '../types/api';

export function getLifetimeGrants(): Promise<{ grants: LifetimeGrantDTO[] }> {
  return apiFetch('/api/admin/lifetime-grants');
}

export function createLifetimeGrant(scope: GrantScope, key: number): Promise<void> {
  return apiFetch('/api/admin/lifetime-grants', {
    method: 'POST',
    body: JSON.stringify({ scope, key }),
  });
}

export function deleteLifetimeGrant(scope: GrantScope, key: number): Promise<void> {
  return apiFetch('/api/admin/lifetime-grants', {
    method: 'DELETE',
    body: JSON.stringify({ scope, key }),
  });
}
```

`frontend/src/api/data.ts`:
```typescript
import { apiFetch } from './client';

export function clearAllData(): Promise<void> {
  return apiFetch('/api/data', { method: 'DELETE' });
}
```

- [ ] **Step 11: Verify typecheck and full test run**

Run: `cd frontend && npm run typecheck && npx vitest run`
Expected: both exit 0; vitest reports all tests (Tasks 2-4) passing.

- [ ] **Step 12: Commit**

```bash
cd frontend
git add src/api
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add domain API modules for every API_CONTRACT.md endpoint"
```

---

### Task 5: Time-range resolution and CSV export libs

**Files:**
- Create: `frontend/src/lib/dateRange.ts`, `frontend/src/lib/dateRange.test.ts`
- Create: `frontend/src/lib/csv.ts`, `frontend/src/lib/csv.test.ts`

**Interfaces:**
- Produces: `TimeRangePreset` type (`'last7' | 'last30' | 'last90' | 'custom' | 'all'`),
  `resolveTimeRange(preset, bounds, custom?): { startTs: number; endTs: number }` — consumed by
  Task 9's Dashboard page. `snapshotsToCsv(snapshots: SnapshotDTO[]): string` and
  `downloadCsv(filename: string, csv: string): void` — consumed by Task 9's CSV export button.

- [ ] **Step 1: Write the failing test for `dateRange.ts`**

`frontend/src/lib/dateRange.test.ts`:
```typescript
import { describe, expect, it } from 'vitest';
import { resolveTimeRange } from './dateRange';

const DAY = 86400;
const bounds = { minTs: 1_700_000_000, maxTs: 1_700_000_000 + 100 * DAY };

describe('resolveTimeRange', () => {
  it('last7 clamps to 7 days before maxTs, floored at minTs', () => {
    expect(resolveTimeRange('last7', bounds)).toEqual({
      startTs: bounds.maxTs - 7 * DAY,
      endTs: bounds.maxTs,
    });
  });

  it('last30 clamps to 30 days before maxTs', () => {
    expect(resolveTimeRange('last30', bounds)).toEqual({
      startTs: bounds.maxTs - 30 * DAY,
      endTs: bounds.maxTs,
    });
  });

  it('last90 floors at minTs when the window would go before it', () => {
    const tightBounds = { minTs: 1_700_000_000, maxTs: 1_700_000_000 + 10 * DAY };
    expect(resolveTimeRange('last90', tightBounds)).toEqual({
      startTs: tightBounds.minTs,
      endTs: tightBounds.maxTs,
    });
  });

  it('all spans the full bounds', () => {
    expect(resolveTimeRange('all', bounds)).toEqual({ startTs: bounds.minTs, endTs: bounds.maxTs });
  });

  it('custom uses the given range, clamped to bounds', () => {
    const custom = { startTs: bounds.minTs + 5 * DAY, endTs: bounds.minTs + 20 * DAY };
    expect(resolveTimeRange('custom', bounds, custom)).toEqual(custom);
  });

  it('custom clamps a range that extends outside bounds', () => {
    const custom = { startTs: bounds.minTs - 10 * DAY, endTs: bounds.maxTs + 10 * DAY };
    expect(resolveTimeRange('custom', bounds, custom)).toEqual({ startTs: bounds.minTs, endTs: bounds.maxTs });
  });

  it('throws if custom is selected without a custom range', () => {
    expect(() => resolveTimeRange('custom', bounds)).toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/dateRange.test.ts`
Expected: FAIL — module doesn't exist yet.

- [ ] **Step 3: Write `frontend/src/lib/dateRange.ts`**

```typescript
export type TimeRangePreset = 'last7' | 'last30' | 'last90' | 'custom' | 'all';

export interface TimeRangeBounds {
  minTs: number;
  maxTs: number;
}

export interface ResolvedRange {
  startTs: number;
  endTs: number;
}

const DAY_SECONDS = 86400;

export function resolveTimeRange(
  preset: TimeRangePreset,
  bounds: TimeRangeBounds,
  custom?: ResolvedRange,
): ResolvedRange {
  const { minTs, maxTs } = bounds;

  if (preset === 'custom') {
    if (!custom) throw new Error('custom preset requires a custom range');
    return {
      startTs: Math.max(minTs, custom.startTs),
      endTs: Math.min(maxTs, custom.endTs),
    };
  }

  const endTs = maxTs;
  let startTs: number;
  switch (preset) {
    case 'last7':
      startTs = Math.max(minTs, endTs - 7 * DAY_SECONDS);
      break;
    case 'last30':
      startTs = Math.max(minTs, endTs - 30 * DAY_SECONDS);
      break;
    case 'last90':
      startTs = Math.max(minTs, endTs - 90 * DAY_SECONDS);
      break;
    case 'all':
      startTs = minTs;
      break;
  }
  return { startTs, endTs };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/dateRange.test.ts`
Expected: PASS (7 tests).

- [ ] **Step 5: Write the failing test for `csv.ts`**

`frontend/src/lib/csv.test.ts`:
```typescript
import { describe, expect, it } from 'vitest';
import { snapshotsToCsv } from './csv';
import type { SnapshotDTO } from '../types/api';

function makeSnapshot(overrides: Partial<SnapshotDTO> = {}): SnapshotDTO {
  return {
    id: 1,
    syncedAt: 1700000000,
    moneyOnhand: 100,
    moneyPoints: 0,
    vaultAmount: 0,
    bankAmount: 0,
    energyCurrent: 10,
    energyMaximum: 150,
    nerveCurrent: 5,
    nerveMaximum: 50,
    happyCurrent: 100,
    happyMaximum: 5000,
    networth: 1000,
    nwPending: 0,
    nwWallet: 100,
    nwBank: 0,
    nwPoints: 0,
    nwCayman: 0,
    nwVault: 0,
    nwPiggybank: 0,
    nwItems: 0,
    nwDisplaycase: 0,
    nwBazaar: 0,
    nwItemmarket: 0,
    nwProperties: 0,
    nwStockmarket: 0,
    nwAuctionhouse: 0,
    nwCompany: 0,
    nwBookie: 0,
    nwEnlistedcars: 0,
    nwLoan: 0,
    nwUnpaidfees: 0,
    refillsTotal: 0,
    nerverefillsTotal: 0,
    energydrinkusedTotal: 0,
    xantakenTotal: 0,
    warModeActive: false,
    note: null,
    ...overrides,
  };
}

describe('snapshotsToCsv', () => {
  it('returns an empty string for an empty list', () => {
    expect(snapshotsToCsv([])).toBe('');
  });

  it('writes a header row of every DTO field', () => {
    const csv = snapshotsToCsv([makeSnapshot()]);
    const [header] = csv.split('\n');
    expect(header).toBe(Object.keys(makeSnapshot()).join(','));
  });

  it('writes one data row per snapshot', () => {
    const csv = snapshotsToCsv([makeSnapshot({ id: 1 }), makeSnapshot({ id: 2 })]);
    expect(csv.split('\n')).toHaveLength(3);
  });

  it('renders null as an empty cell', () => {
    const csv = snapshotsToCsv([makeSnapshot({ note: null })]);
    const [, row] = csv.split('\n');
    const noteIndex = Object.keys(makeSnapshot()).indexOf('note');
    expect(row.split(',')[noteIndex]).toBe('');
  });

  it('quotes a value containing a comma', () => {
    const csv = snapshotsToCsv([makeSnapshot({ note: 'War week 1, day 3' })]);
    expect(csv).toContain('"War week 1, day 3"');
  });
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/csv.test.ts`
Expected: FAIL — module doesn't exist yet.

- [ ] **Step 7: Write `frontend/src/lib/csv.ts`**

```typescript
import type { SnapshotDTO } from '../types/api';

export function snapshotsToCsv(snapshots: SnapshotDTO[]): string {
  if (snapshots.length === 0) return '';

  const headers = Object.keys(snapshots[0]) as (keyof SnapshotDTO)[];
  const lines = [headers.join(',')];
  for (const snapshot of snapshots) {
    lines.push(headers.map((h) => csvCell(snapshot[h])).join(','));
  }
  return lines.join('\n');
}

function csvCell(value: unknown): string {
  if (value === null || value === undefined) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function downloadCsv(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/csv.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 9: Commit**

```bash
cd frontend
git add src/lib/dateRange.ts src/lib/dateRange.test.ts src/lib/csv.ts src/lib/csv.test.ts
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add time-range resolution and CSV export helpers"
```

---

### Task 6: MSW dev-mock server

**Files:**
- Create: `frontend/src/mocks/data.ts`, `frontend/src/mocks/handlers.ts`, `frontend/src/mocks/browser.ts`
- Create (generated): `frontend/public/mockServiceWorker.js`
- Modify: `frontend/.env.example` (document `VITE_USE_MOCKS`/empty-`VITE_API_BASE_URL` pairing)

**Interfaces:**
- Consumes: every DTO type from `../types/api`.
- Produces: `handlers` (array of MSW request handlers covering every `API_CONTRACT.md` endpoint),
  `worker` (an MSW `setupWorker` instance) — consumed by Task 7's `main.tsx`. This task has no
  automated tests (it's dev-only fixture/mock code, not app logic) — verified by Task 7's browser
  click-through instead.

- [ ] **Step 1: Generate the MSW service worker file**

```bash
cd frontend
npx msw init public --save
```
Expected: creates `frontend/public/mockServiceWorker.js` and adds a `"msw"` key to `package.json`.

- [ ] **Step 2: Write `frontend/src/mocks/data.ts`**

```typescript
import type {
  ChecklistTaskDTO,
  LifetimeGrantDTO,
  LogEntryDTO,
  PlayerDTO,
  PremiumStatusDTO,
  SnapshotDTO,
  WarModeDTO,
} from '../types/api';

export const mockSession = { loggedIn: false, trialUsed: false };

export const mockPlayer: PlayerDTO = {
  playerId: 4316364,
  name: 'MockPlayer',
  factionId: 7890,
  maskedApiKey: '****mock',
  isAdmin: true,
};

export const mockPremium: PremiumStatusDTO = {
  isPremium: true,
  premiumUntil: Math.floor(Date.now() / 1000) + 10 * 86400,
  isLifetime: false,
  source: 'individual',
  isExpiringSoon: false,
  daysUntilExpiry: 10,
};

function makeSnapshot(daysAgo: number, overrides: Partial<SnapshotDTO> = {}): SnapshotDTO {
  const syncedAt = Math.floor(Date.now() / 1000) - daysAgo * 86400;
  return {
    id: 1000 - daysAgo,
    syncedAt,
    moneyOnhand: 500000 + daysAgo * 1000,
    moneyPoints: 12000,
    vaultAmount: 2000000,
    bankAmount: 100000,
    energyCurrent: 90,
    energyMaximum: 150,
    nerveCurrent: 20,
    nerveMaximum: 50,
    happyCurrent: 4000,
    happyMaximum: 5000,
    networth: 15000000 - daysAgo * 20000,
    nwPending: 0,
    nwWallet: 500000,
    nwBank: 100000,
    nwPoints: 1200000,
    nwCayman: 0,
    nwVault: 2000000,
    nwPiggybank: 0,
    nwItems: 3000000,
    nwDisplaycase: 0,
    nwBazaar: 0,
    nwItemmarket: 0,
    nwProperties: 5000000,
    nwStockmarket: 0,
    nwAuctionhouse: 0,
    nwCompany: 0,
    nwBookie: 0,
    nwEnlistedcars: 0,
    nwLoan: 0,
    nwUnpaidfees: 0,
    refillsTotal: 40,
    nerverefillsTotal: 5,
    energydrinkusedTotal: 12,
    xantakenTotal: 8,
    warModeActive: false,
    note: daysAgo === 0 ? 'Latest sync' : null,
    ...overrides,
  };
}

export const mockSnapshots: SnapshotDTO[] = Array.from({ length: 14 }, (_, i) => makeSnapshot(13 - i));

export const mockLogEntries: LogEntryDTO[] = [
  {
    id: 1,
    tornLogId: '111',
    timestamp: Math.floor(Date.now() / 1000) - 2 * 86400,
    category: 'Attacking',
    title: 'Attacked player X',
    rawText: 'You attacked player X and won, gaining $50,000',
    amount: 50000,
    appCategory: 'Ranked War',
    userNote: null,
  },
  {
    id: 2,
    tornLogId: '112',
    timestamp: Math.floor(Date.now() / 1000) - 1 * 86400,
    category: 'Item sending',
    title: 'Item send',
    rawText: 'You sent 4x Xanax to SomePlayer',
    amount: null,
    appCategory: 'Uncategorized',
    userNote: null,
  },
  {
    id: 3,
    tornLogId: '113',
    timestamp: Math.floor(Date.now() / 1000) - 3 * 3600,
    category: 'Job',
    title: 'Received company pay',
    rawText: 'You worked a shift and earned $12,000',
    amount: 12000,
    appCategory: 'Job',
    userNote: null,
  },
  {
    id: 4,
    tornLogId: '114',
    timestamp: Math.floor(Date.now() / 1000) - 5 * 3600,
    category: 'Mystery',
    title: 'Unusual event',
    rawText: 'Something happened that nothing recognizes',
    amount: -3000,
    appCategory: 'Uncategorized',
    userNote: null,
  },
];

export const mockCategories: string[] = ['Ranked War', 'Flying', 'Job', 'Gift', 'Casino'];

export const mockChecklistTasks: ChecklistTaskDTO[] = [
  {
    id: 1,
    title: 'Use energy refill',
    description: 'Spend the daily energy refill before it resets.',
    repeatType: 'daily',
    repeatIntervalDays: null,
    createdAt: Math.floor(Date.now() / 1000) - 30 * 86400,
    lastCompletedAt: null,
    isDoneCurrentCycle: false,
  },
  {
    id: 2,
    title: 'Check faction OCs',
    description: null,
    repeatType: 'every_x_days',
    repeatIntervalDays: 2,
    createdAt: Math.floor(Date.now() / 1000) - 20 * 86400,
    lastCompletedAt: null,
    isDoneCurrentCycle: false,
  },
  {
    id: 3,
    title: 'Rotate war targets',
    description: 'Only shown while War Mode is active.',
    repeatType: 'war_day',
    repeatIntervalDays: null,
    createdAt: Math.floor(Date.now() / 1000) - 5 * 86400,
    lastCompletedAt: null,
    isDoneCurrentCycle: false,
  },
];

export const mockWarMode: WarModeDTO = { active: false, startedAt: null };

export const mockLifetimeGrants: LifetimeGrantDTO[] = [
  { scope: 'individual', key: 1234567, activatedAt: Math.floor(Date.now() / 1000) - 100 * 86400 },
];
```

- [ ] **Step 3: Write `frontend/src/mocks/handlers.ts`**

```typescript
import { delay, http, HttpResponse } from 'msw';
import {
  mockCategories,
  mockChecklistTasks,
  mockLifetimeGrants,
  mockLogEntries,
  mockPlayer,
  mockPremium,
  mockSession,
  mockSnapshots,
  mockWarMode,
} from './data';
import type { ChecklistTaskDTO, FullHistoryJobDTO, LogEntryDTO, SnapshotDTO } from '../types/api';

function errorBody(message: string, code: string, tornErrorCode: number | null = null) {
  return { error: { message, code, tornErrorCode } };
}

let nextChecklistId = 100;
let nextLogEntryId = 100;
let nextJobId = 1;
const fullHistoryJobs = new Map<number, FullHistoryJobDTO>();

function categoryCount(name: string): number {
  return mockLogEntries.filter((e) => e.appCategory === name).length;
}

function simulateFullHistoryProgress(job: FullHistoryJobDTO): void {
  let tick = 0;
  const interval = setInterval(() => {
    tick += 1;
    if (tick <= 4) {
      job.pagesFetched = tick;
      job.entriesFetched = tick * 300;
      job.oldestTimestamp = Math.floor(Date.now() / 1000) - tick * 30 * 86400;
    } else {
      job.status = 'completed';
      job.result = { newEntriesStored: 1180, alreadyStored: 40 };
      clearInterval(interval);
    }
  }, 1200);
}

export const handlers = [
  http.get('/api/auth/me', async () => {
    await delay(800);
    if (!mockSession.loggedIn) {
      return HttpResponse.json(errorBody('Not signed in.', 'not_authenticated'), { status: 401 });
    }
    return HttpResponse.json({ player: mockPlayer, premium: mockPremium });
  }),

  http.post('/api/auth/login', async ({ request }) => {
    const body = (await request.json()) as { apiKey: string };
    if (!body.apiKey || !body.apiKey.trim()) {
      return HttpResponse.json(errorBody('Enter a key before saving.', 'invalid_request'), { status: 400 });
    }
    if (body.apiKey.trim() === 'invalid') {
      return HttpResponse.json(errorBody('Incorrect API key.', 'invalid_key', 2), { status: 401 });
    }
    mockSession.loggedIn = true;
    return HttpResponse.json({ player: mockPlayer, premium: mockPremium });
  }),

  http.post('/api/auth/logout', () => {
    mockSession.loggedIn = false;
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/snapshots', ({ request }) => {
    const url = new URL(request.url);
    const startTs = url.searchParams.get('startTs');
    const endTs = url.searchParams.get('endTs');
    let rows = mockSnapshots;
    if (startTs) rows = rows.filter((s) => s.syncedAt >= Number(startTs));
    if (endTs) rows = rows.filter((s) => s.syncedAt <= Number(endTs));
    return HttpResponse.json({ snapshots: rows });
  }),

  http.get('/api/snapshots/latest', () => {
    const snapshot = mockSnapshots.length ? mockSnapshots[mockSnapshots.length - 1] : null;
    return HttpResponse.json({ snapshot });
  }),

  http.patch('/api/snapshots/:id/note', async ({ params, request }) => {
    const { note } = (await request.json()) as { note: string };
    const snapshot = mockSnapshots.find((s) => s.id === Number(params.id));
    if (!snapshot) return HttpResponse.json(errorBody('Snapshot not found.', 'not_found'), { status: 404 });
    snapshot.note = note;
    return HttpResponse.json({ snapshot });
  }),

  http.get('/api/dashboard', ({ request }) => {
    const url = new URL(request.url);
    const startTs = Number(url.searchParams.get('startTs'));
    const endTs = Number(url.searchParams.get('endTs'));
    const snapshots = mockSnapshots.filter((s) => s.syncedAt >= startTs && s.syncedAt <= endTs);
    const entries = mockLogEntries.filter((e) => e.timestamp >= startTs && e.timestamp <= endTs);
    const countable = entries.filter((e) => e.amount !== null && e.appCategory !== 'Ignored');
    const cashflowTotal = countable.reduce((sum, e) => sum + (e.amount ?? 0), 0);
    const days = Math.max((endTs - startTs) / 86400, 1);
    const cashflowPerDay = cashflowTotal / days;

    const byCategory = new Map<string, number>();
    for (const e of countable) {
      byCategory.set(e.appCategory, (byCategory.get(e.appCategory) ?? 0) + (e.amount ?? 0));
    }

    const latest = snapshots[snapshots.length - 1] ?? mockSnapshots[mockSnapshots.length - 1];
    const networthBreakdown = [
      { component: 'Networth Total', amount: latest.networth },
      { component: 'Pending', amount: latest.nwPending },
      { component: 'Wallet', amount: latest.nwWallet },
      { component: 'Bank', amount: latest.nwBank },
      { component: 'Points @ $', amount: latest.nwPoints },
      { component: 'Cayman', amount: latest.nwCayman },
      { component: 'Vault', amount: latest.nwVault },
      { component: 'Piggy Bank', amount: latest.nwPiggybank },
      { component: 'Items', amount: latest.nwItems },
      { component: 'Display Case', amount: latest.nwDisplaycase },
      { component: 'Bazaar', amount: latest.nwBazaar },
      { component: 'Trade', amount: null },
      { component: 'Items Market', amount: latest.nwItemmarket },
      { component: 'Properties', amount: latest.nwProperties },
      { component: 'Stock Market', amount: latest.nwStockmarket },
      { component: 'Auction House', amount: latest.nwAuctionhouse },
      { component: 'Company', amount: latest.nwCompany },
      { component: 'Bookie', amount: latest.nwBookie },
      { component: 'Enlisted Cars', amount: latest.nwEnlistedcars },
      { component: 'Loan', amount: latest.nwLoan },
      { component: 'Unpaid Fees', amount: latest.nwUnpaidfees },
    ];

    const dailyCashflowMap = new Map<string, number>();
    for (const e of countable) {
      const date = new Date(e.timestamp * 1000).toISOString().slice(0, 10);
      dailyCashflowMap.set(date, (dailyCashflowMap.get(date) ?? 0) + (e.amount ?? 0));
    }
    const dailyNetworthMap = new Map<string, number>();
    for (const s of snapshots) {
      const date = new Date(s.syncedAt * 1000).toISOString().slice(0, 10);
      dailyNetworthMap.set(date, s.networth);
    }

    return HttpResponse.json({
      cashflowTotal,
      cashflowPerDay,
      categoryBreakdown: [...byCategory.entries()].map(([category, amount]) => ({ category, amount })),
      networthBreakdown,
      dailyCashflow: [...dailyCashflowMap.entries()].map(([date, cashflowDelta]) => ({ date, cashflowDelta })),
      dailyNetworth: [...dailyNetworthMap.entries()].map(([date, networth]) => ({ date, networth })),
      snapshots,
    });
  }),

  http.get('/api/log-entries/uncategorized', ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 25);
    const all = mockLogEntries.filter((e) => e.appCategory === 'Uncategorized');
    return HttpResponse.json({ entries: all.slice(0, limit), totalCount: all.length });
  }),

  http.get('/api/log-entries/ignored', ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get('limit') ?? 25);
    const all = mockLogEntries.filter((e) => e.appCategory === 'Ignored');
    return HttpResponse.json({ entries: all.slice(0, limit), totalCount: all.length });
  }),

  http.get('/api/log-entries', ({ request }) => {
    const category = new URL(request.url).searchParams.get('category');
    const rows = category ? mockLogEntries.filter((e) => e.appCategory === category) : mockLogEntries;
    return HttpResponse.json({ entries: rows });
  }),

  http.patch('/api/log-entries/:id', async ({ params, request }) => {
    const { appCategory, userNote } = (await request.json()) as { appCategory: string; userNote: string | null };
    const entry = mockLogEntries.find((e) => e.id === Number(params.id));
    if (!entry) return HttpResponse.json(errorBody('Entry not found.', 'not_found'), { status: 404 });
    entry.appCategory = appCategory;
    entry.userNote = userNote;
    let bulkUpdatedCount = 0;
    if (entry.title) {
      for (const other of mockLogEntries) {
        if (other.id !== entry.id && other.title === entry.title && other.appCategory === 'Uncategorized') {
          other.appCategory = appCategory;
          bulkUpdatedCount += 1;
        }
      }
    }
    return HttpResponse.json({ entry, bulkUpdatedCount });
  }),

  http.post('/api/log-entries/:id/ignore', async ({ params, request }) => {
    const { userNote } = (await request.json()) as { userNote: string | null };
    const entry = mockLogEntries.find((e) => e.id === Number(params.id));
    if (!entry) return HttpResponse.json(errorBody('Entry not found.', 'not_found'), { status: 404 });
    entry.appCategory = 'Ignored';
    entry.userNote = userNote;
    let bulkUpdatedCount = 0;
    if (entry.title) {
      for (const other of mockLogEntries) {
        if (other.id !== entry.id && other.title === entry.title && other.appCategory === 'Uncategorized') {
          other.appCategory = 'Ignored';
          bulkUpdatedCount += 1;
        }
      }
    }
    return HttpResponse.json({ entry, bulkUpdatedCount });
  }),

  http.post('/api/log-entries/:id/restore', ({ params }) => {
    const entry = mockLogEntries.find((e) => e.id === Number(params.id));
    if (!entry) return HttpResponse.json(errorBody('Entry not found.', 'not_found'), { status: 404 });
    entry.appCategory = 'Uncategorized';
    return HttpResponse.json({ entry });
  }),

  http.post('/api/log-entries/recategorize-period', async ({ request }) => {
    const { startTs, endTs, appCategory } = (await request.json()) as {
      startTs: number;
      endTs: number;
      appCategory: string;
    };
    let updatedCount = 0;
    for (const entry of mockLogEntries) {
      if (entry.timestamp >= startTs && entry.timestamp <= endTs) {
        entry.appCategory = appCategory;
        updatedCount += 1;
      }
    }
    return HttpResponse.json({ updatedCount });
  }),

  http.get('/api/categories', () => {
    return HttpResponse.json({ categories: mockCategories.map((name) => ({ name, entryCount: categoryCount(name) })) });
  }),

  http.post('/api/categories', async ({ request }) => {
    const { name } = (await request.json()) as { name: string };
    if (name === 'Uncategorized' || name === 'Ignored' || mockCategories.includes(name)) {
      return HttpResponse.json(errorBody(`'${name}' already exists or is reserved.`, 'category_conflict'), { status: 409 });
    }
    mockCategories.push(name);
    return HttpResponse.json({ name }, { status: 201 });
  }),

  http.delete('/api/categories/:name', ({ params }) => {
    const name = decodeURIComponent(params.name as string);
    if (categoryCount(name) > 0) {
      return HttpResponse.json(errorBody(`'${name}' is still used by log entries.`, 'category_in_use'), { status: 409 });
    }
    const index = mockCategories.indexOf(name);
    if (index !== -1) mockCategories.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.get('/api/categories/title-summary', ({ request }) => {
    const filter = new URL(request.url).searchParams.get('filterCategory');
    const byTitle = new Map<string, { title: string; category: string; entryCount: number }>();
    for (const entry of mockLogEntries) {
      if (filter && entry.appCategory !== filter) continue;
      const key = `${entry.title}::${entry.appCategory}`;
      const existing = byTitle.get(key);
      if (existing) existing.entryCount += 1;
      else byTitle.set(key, { title: entry.title, category: entry.appCategory, entryCount: 1 });
    }
    return HttpResponse.json({ rows: [...byTitle.values()] });
  }),

  http.post('/api/categories/reassign', async ({ request }) => {
    const { title, fromCategory, toCategory } = (await request.json()) as {
      title: string;
      fromCategory: string;
      toCategory: string;
    };
    let updatedCount = 0;
    for (const entry of mockLogEntries) {
      if (entry.title === title && entry.appCategory === fromCategory) {
        entry.appCategory = toCategory;
        updatedCount += 1;
      }
    }
    return HttpResponse.json({ updatedCount });
  }),

  http.post('/api/sync/incremental', async () => {
    await delay(500);
    const now = Math.floor(Date.now() / 1000);
    const snapshot: SnapshotDTO = { ...mockSnapshots[mockSnapshots.length - 1], id: mockSnapshots.length + 1000, syncedAt: now, note: null };
    mockSnapshots.push(snapshot);
    const newEntry: LogEntryDTO = {
      id: nextLogEntryId++,
      tornLogId: String(900000 + nextLogEntryId),
      timestamp: now,
      category: 'Attacking',
      title: 'Attacked player Y',
      rawText: 'You attacked player Y and won, gaining $8,000',
      amount: 8000,
      appCategory: 'Ranked War',
      userNote: null,
    };
    mockLogEntries.push(newEntry);
    return HttpResponse.json({ snapshot, logEntriesStored: 1, paymentMessage: null });
  }),

  http.post('/api/sync/full-history', () => {
    const jobId = nextJobId++;
    const job: FullHistoryJobDTO = {
      jobId,
      status: 'running',
      pagesFetched: 0,
      entriesFetched: 0,
      oldestTimestamp: null,
      error: null,
      result: null,
    };
    fullHistoryJobs.set(jobId, job);
    simulateFullHistoryProgress(job);
    return HttpResponse.json({ jobId, status: 'running' }, { status: 202 });
  }),

  http.get('/api/sync/full-history/:jobId', ({ params }) => {
    const job = fullHistoryJobs.get(Number(params.jobId));
    if (!job) return HttpResponse.json(errorBody('Job not found.', 'not_found'), { status: 404 });
    return HttpResponse.json(job);
  }),

  http.get('/api/checklist', () => HttpResponse.json({ tasks: mockChecklistTasks })),

  http.post('/api/checklist', async ({ request }) => {
    const input = (await request.json()) as Omit<ChecklistTaskDTO, 'id' | 'createdAt' | 'lastCompletedAt' | 'isDoneCurrentCycle'>;
    const task: ChecklistTaskDTO = {
      id: nextChecklistId++,
      title: input.title,
      description: input.description || null,
      repeatType: input.repeatType,
      repeatIntervalDays: input.repeatType === 'every_x_days' ? input.repeatIntervalDays : null,
      createdAt: Math.floor(Date.now() / 1000),
      lastCompletedAt: null,
      isDoneCurrentCycle: false,
    };
    mockChecklistTasks.push(task);
    return HttpResponse.json({ task }, { status: 201 });
  }),

  http.patch('/api/checklist/:id', async ({ params, request }) => {
    const input = (await request.json()) as Omit<ChecklistTaskDTO, 'id' | 'createdAt' | 'lastCompletedAt' | 'isDoneCurrentCycle'>;
    const task = mockChecklistTasks.find((t) => t.id === Number(params.id));
    if (!task) return HttpResponse.json(errorBody('Task not found.', 'not_found'), { status: 404 });
    task.title = input.title;
    task.description = input.description || null;
    task.repeatType = input.repeatType;
    task.repeatIntervalDays = input.repeatType === 'every_x_days' ? input.repeatIntervalDays : null;
    return HttpResponse.json({ task });
  }),

  http.delete('/api/checklist/:id', ({ params }) => {
    const index = mockChecklistTasks.findIndex((t) => t.id === Number(params.id));
    if (index !== -1) mockChecklistTasks.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.post('/api/checklist/:id/done', async ({ params, request }) => {
    const { done } = (await request.json()) as { done: boolean };
    const task = mockChecklistTasks.find((t) => t.id === Number(params.id));
    if (!task) return HttpResponse.json(errorBody('Task not found.', 'not_found'), { status: 404 });
    task.isDoneCurrentCycle = done;
    if (done) task.lastCompletedAt = Math.floor(Date.now() / 1000);
    return HttpResponse.json({ task });
  }),

  http.get('/api/settings/war-mode', () => HttpResponse.json(mockWarMode)),

  http.put('/api/settings/war-mode', async ({ request }) => {
    const { active } = (await request.json()) as { active: boolean };
    mockWarMode.active = active;
    if (active) mockWarMode.startedAt = Math.floor(Date.now() / 1000);
    return HttpResponse.json(mockWarMode);
  }),

  http.get('/api/licensing/status', () => HttpResponse.json({ ...mockPremium, trialUsed: mockSession.trialUsed })),

  http.post('/api/licensing/trial', () => {
    if (mockSession.trialUsed) {
      return HttpResponse.json({ started: false, reason: 'Trial already used.', premiumUntil: null });
    }
    mockSession.trialUsed = true;
    const premiumUntil = Math.floor(Date.now() / 1000) + 7 * 86400;
    mockPremium.isPremium = true;
    mockPremium.premiumUntil = premiumUntil;
    mockPremium.source = 'trial';
    return HttpResponse.json({ started: true, reason: null, premiumUntil });
  }),

  http.post('/api/licensing/scan-payment', () =>
    HttpResponse.json({ creditedCount: 0, weeksAdded: 0, newPremiumUntil: null, alreadyCreditedCount: 0 }),
  ),

  http.get('/api/licensing/faction-preview', () => {
    if (!mockPlayer.factionId) return new HttpResponse(null, { status: 204 });
    return HttpResponse.json({ memberCount: 34, lifetimeCoveredCount: 2, payableMembers: 32, discountPct: 0.1, required: 29 });
  }),

  http.post('/api/licensing/scan-group-payment', () =>
    HttpResponse.json({ activated: false, message: "Sent 0, need 29 for your faction's 34 members.", required: 29, sent: 0 }),
  ),

  http.get('/api/admin/lifetime-grants', () => HttpResponse.json({ grants: mockLifetimeGrants })),

  http.post('/api/admin/lifetime-grants', async ({ request }) => {
    const grant = (await request.json()) as { scope: 'individual' | 'faction'; key: number };
    mockLifetimeGrants.push({ ...grant, activatedAt: Math.floor(Date.now() / 1000) });
    return new HttpResponse(null, { status: 201 });
  }),

  http.delete('/api/admin/lifetime-grants', async ({ request }) => {
    const { scope, key } = (await request.json()) as { scope: 'individual' | 'faction'; key: number };
    const index = mockLifetimeGrants.findIndex((g) => g.scope === scope && g.key === key);
    if (index !== -1) mockLifetimeGrants.splice(index, 1);
    return new HttpResponse(null, { status: 204 });
  }),

  http.delete('/api/data', () => {
    mockSnapshots.length = 0;
    mockLogEntries.length = 0;
    return new HttpResponse(null, { status: 204 });
  }),
];
```

- [ ] **Step 4: Write `frontend/src/mocks/browser.ts`**

```typescript
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
```

- [ ] **Step 5: Document the mock env pairing in `frontend/.env.example`**

Update `frontend/.env.example` to:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCKS=false

# For local dev-only click-through against the MSW mocks (no real backend needed):
# VITE_API_BASE_URL=
# VITE_USE_MOCKS=true
```

- [ ] **Step 6: Verify typecheck**

Run: `cd frontend && npm run typecheck`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
cd frontend
git add public/mockServiceWorker.js src/mocks .env.example package.json
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add MSW dev-mock server covering every API_CONTRACT.md endpoint"
```

---

### Task 7: Auth hook, routing shell, Login page

**Files:**
- Create: `frontend/src/constants.ts`
- Create: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/components/loading/ColdStartLoader.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/pages/Login.tsx`
- Create (placeholders, replaced by Tasks 8-13): `frontend/src/pages/Home.tsx`, `Dashboard.tsx`, `Sync.tsx`, `Checklist.tsx`, `Settings.tsx`, `Categories.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`

**Interfaces:**
- Consumes: `getMe`, `login`, `logout` (Task 4), `ApiError` (Task 3), UI primitives (Task 2), MSW
  `worker` (Task 6).
- Produces: `useAuth()` returning `{ player, premium, isLoading, isAuthenticated, isUnauthenticated,
  error, refetch }`; `useInvalidateAuth()` returning a no-arg function; `AUTH_QUERY_KEY` — consumed
  by every later page task that needs `player`/`premium` or must invalidate the session after a
  mutation. Constants `GITHUB_REPO_URL`, `DEV_TORN_PLAYER_ID`, `DEV_TORN_PLAYER_NAME`,
  `DEV_PROFILE_URL`, `DEV_PROFILE_LABEL`, `API_KEY_CREATE_URL` from `constants.ts` — consumed by
  Task 8 (Home) and Task 12 (Settings).

- [ ] **Step 1: Write `frontend/src/constants.ts`**

```typescript
export const GITHUB_REPO_URL = 'https://github.com/M3mphistus/torn_cashflow';
export const DEV_TORN_PLAYER_ID = 4316364;
export const DEV_TORN_PLAYER_NAME = 'the developer';
export const DEV_PROFILE_URL = `https://www.torn.com/profiles.php?XID=${DEV_TORN_PLAYER_ID}`;
export const DEV_PROFILE_LABEL = `${DEV_TORN_PLAYER_NAME} [${DEV_TORN_PLAYER_ID}]`;
export const API_KEY_CREATE_URL =
  'https://www.torn.com/preferences.php#tab=api?step=addNewKey&title=Torn%20Cashflow%20Dashboard&user=basic,profile,bars,money,personalstats,log';
```

- [ ] **Step 2: Write `frontend/src/hooks/useAuth.ts`**

```typescript
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import { getMe } from '../api/auth';
import type { PlayerDTO, PremiumStatusDTO } from '../types/api';

export const AUTH_QUERY_KEY = ['auth', 'me'] as const;

export interface AuthState {
  player: PlayerDTO | null;
  premium: PremiumStatusDTO | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isUnauthenticated: boolean;
  error: unknown;
  refetch: () => void;
}

export function useAuth(): AuthState {
  const query = useQuery({ queryKey: AUTH_QUERY_KEY, queryFn: getMe, retry: false });
  const isAuthError = query.error instanceof ApiError && query.error.status === 401;

  return {
    player: query.data?.player ?? null,
    premium: query.data?.premium ?? null,
    isLoading: query.isLoading,
    isAuthenticated: query.isSuccess,
    isUnauthenticated: query.isError && isAuthError,
    error: query.isError && !isAuthError ? query.error : null,
    refetch: () => query.refetch(),
  };
}

export function useInvalidateAuth() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
}
```

- [ ] **Step 3: Write `frontend/src/components/loading/ColdStartLoader.tsx`**

```tsx
export default function ColdStartLoader() {
  return (
    <div className="page" style={{ textAlign: 'center', paddingTop: '15vh' }}>
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Waking up the server&hellip;</h1>
      <p>
        The backend spins down after a period of inactivity — this can take up to a minute the
        first time. Hang tight, it only happens once per idle period.
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Write `frontend/src/pages/Login.tsx`**

```tsx
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { login } from '../api/auth';
import { ApiError } from '../api/client';
import { useInvalidateAuth } from '../hooks/useAuth';
import Card from '../components/ui/Card';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import { API_KEY_CREATE_URL } from '../constants';

export default function LoginPage() {
  const [apiKey, setApiKey] = useState('');
  const invalidateAuth = useInvalidateAuth();
  const mutation = useMutation({
    mutationFn: () => login(apiKey.trim()),
    onSuccess: () => invalidateAuth(),
  });

  return (
    <div className="page" style={{ maxWidth: 520 }}>
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Torn Cashflow Dashboard</h1>
      <p>
        Paste a Torn API key to sign in. Use a scoped, read-only key —{' '}
        <a href={API_KEY_CREATE_URL} target="_blank" rel="noreferrer">
          click here to create one
        </a>{' '}
        with exactly the permissions this app needs pre-checked. No blanket Full Access required.
      </p>

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            mutation.mutate();
          }}
        >
          <label htmlFor="api-key">Torn API key</label>
          <input id="api-key" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} autoComplete="off" />
          <div style={{ marginTop: 12 }}>
            <Button type="submit" variant="primary" disabled={mutation.isPending || !apiKey.trim()}>
              {mutation.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </div>
        </form>
      </Card>

      {mutation.isError && (
        <AlertBanner kind="error">{mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}</AlertBanner>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Write `frontend/src/components/layout/AppShell.tsx`**

```tsx
import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { logout } from '../../api/auth';
import { useInvalidateAuth } from '../../hooks/useAuth';
import PremiumBadge from '../ui/PremiumBadge';
import Button from '../ui/Button';
import type { PlayerDTO, PremiumStatusDTO } from '../../types/api';

const NAV_ITEMS = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/sync', label: 'Sync' },
  { to: '/checklist', label: 'Checklist' },
  { to: '/categories', label: 'Categories' },
  { to: '/settings', label: 'Settings' },
];

export default function AppShell({
  player,
  premium,
  children,
}: {
  player: PlayerDTO;
  premium: PremiumStatusDTO;
  children: ReactNode;
}) {
  const invalidateAuth = useInvalidateAuth();
  const logoutMutation = useMutation({ mutationFn: logout, onSuccess: () => invalidateAuth() });

  return (
    <div>
      <div className="app-shell-top">
        <nav className="app-shell-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
              {item.to === '/categories' && !premium.isPremium && <PremiumBadge />}
            </NavLink>
          ))}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="eyebrow">
            {player.name} {premium.isPremium && <PremiumBadge />}
          </span>
          <Button onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
            Log out
          </Button>
        </div>
      </div>
      {children}
    </div>
  );
}
```

- [ ] **Step 6: Write placeholder page components (replaced by Tasks 8-13)**

Each of `frontend/src/pages/Home.tsx`, `Dashboard.tsx`, `Sync.tsx`, `Checklist.tsx`, `Settings.tsx`, `Categories.tsx` gets this pattern (substitute the page name):

```tsx
export default function HomePage() {
  return (
    <div className="page">
      <h1>Home</h1>
      <p>Coming in a later task.</p>
    </div>
  );
}
```

- [ ] **Step 7: Rewrite `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import ColdStartLoader from './components/loading/ColdStartLoader';
import AppShell from './components/layout/AppShell';
import AlertBanner from './components/ui/AlertBanner';
import Button from './components/ui/Button';
import LoginPage from './pages/Login';
import HomePage from './pages/Home';
import DashboardPage from './pages/Dashboard';
import SyncPage from './pages/Sync';
import ChecklistPage from './pages/Checklist';
import SettingsPage from './pages/Settings';
import CategoriesPage from './pages/Categories';

export default function App() {
  const auth = useAuth();

  if (auth.isLoading) return <ColdStartLoader />;

  if (auth.error) {
    return (
      <div className="page">
        <AlertBanner kind="error">Could not reach the server. It may still be waking up.</AlertBanner>
        <Button onClick={() => auth.refetch()}>Try again</Button>
      </div>
    );
  }

  if (!auth.isAuthenticated || !auth.player || !auth.premium) {
    return <LoginPage />;
  }

  return (
    <BrowserRouter>
      <AppShell player={auth.player} premium={auth.premium}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/sync" element={<SyncPage />} />
          <Route path="/checklist" element={<ChecklistPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
```

- [ ] **Step 8: Rewrite `frontend/src/main.tsx`**

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './styles/theme.css';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

async function enableMocking(): Promise<void> {
  if (import.meta.env.VITE_USE_MOCKS !== 'true') return;
  const { worker } = await import('./mocks/browser');
  await worker.start({ onUnhandledRequest: 'bypass' });
}

enableMocking().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </StrictMode>,
  );
});
```

- [ ] **Step 9: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 10: Manually verify the auth flow in the browser**

```bash
cd frontend
printf 'VITE_API_BASE_URL=\nVITE_USE_MOCKS=true\n' > .env
npm run dev
```
Open the dev server URL in the browser preview. Confirm:
- The "Waking up the server…" panel appears briefly (the mock `/api/auth/me` handler has an
  800ms delay), then the Login page renders (mock starts logged out).
- Typing `invalid` as the API key and submitting shows the `ApiError` message ("Incorrect API
  key.") from the mock.
- Typing any other non-empty key and submitting logs in and renders the app shell with nav links,
  the mock player's name, and a Log out button.
- Clicking Log out returns to the Login page.
Stop the dev server when done (`Ctrl+C`); leave `.env` in place for later tasks' verification (it's gitignored, not committed).

- [ ] **Step 11: Commit**

```bash
cd frontend
git add src/constants.ts src/hooks src/components/loading src/components/layout src/pages App.tsx main.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add auth flow, routing shell, and Login page"
```

---

### Task 8: Home page

**Files:**
- Create: `frontend/src/components/layout/NavCard.tsx`
- Modify: `frontend/src/pages/Home.tsx` (replaces Task 7's placeholder)

**Interfaces:**
- Consumes: `useAuth()` (Task 7), `getLatestSnapshot` (Task 4), `formatTimestamp`, `formatDays`
  (Task 2), `Card`/`AlertBanner`/`PremiumBadge` (Task 2), `GITHUB_REPO_URL`/`DEV_PROFILE_URL`/
  `DEV_PROFILE_LABEL` (Task 7's `constants.ts`).
- Produces: `NavCard` component (props: `to: string`, `title: string`, `caption: string`,
  `premium?: boolean`) — reusable if a later page needs a similar link-card, though only Home uses
  it today.

- [ ] **Step 1: Write `frontend/src/components/layout/NavCard.tsx`**

```tsx
import { Link } from 'react-router-dom';
import Card from '../ui/Card';
import SectionHeading from '../ui/SectionHeading';

export default function NavCard({
  to,
  title,
  caption,
  premium = false,
}: {
  to: string;
  title: string;
  caption: string;
  premium?: boolean;
}) {
  return (
    <Link to={to} className="nav-card">
      <Card>
        <SectionHeading premium={premium}>{title}</SectionHeading>
        <p style={{ color: 'var(--text-mute)', fontSize: 13 }}>{caption}</p>
      </Card>
    </Link>
  );
}
```

- [ ] **Step 2: Write `frontend/src/pages/Home.tsx`**

```tsx
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getLatestSnapshot } from '../api/snapshots';
import AlertBanner from '../components/ui/AlertBanner';
import NavCard from '../components/layout/NavCard';
import { formatTimestamp, formatDays } from '../lib/format';
import { GITHUB_REPO_URL, DEV_PROFILE_URL, DEV_PROFILE_LABEL } from '../constants';

export default function HomePage() {
  const { player, premium } = useAuth();
  const { data } = useQuery({ queryKey: ['snapshots', 'latest'], queryFn: getLatestSnapshot });
  const latest = data?.snapshot ?? null;

  return (
    <div className="page">
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Torn Cashflow Dashboard</h1>
      <p>
        Track your cashflow, energy/nerve spend, networth, and a recurring checklist — all pulled
        straight from your own Torn account. Create a scoped API key once in Settings and you'll
        stay signed in on this browser.
      </p>

      {player && (
        <AlertBanner kind="success">
          Signed in as <strong>{player.name}</strong> (player id {player.playerId})
          {player.factionId ? ` — faction ${player.factionId}` : ''}.
        </AlertBanner>
      )}

      {premium?.isExpiringSoon && premium.daysUntilExpiry !== null && (
        <AlertBanner kind="warning">
          Your Premium expires in <strong>{formatDays(premium.daysUntilExpiry)} day(s)</strong> —
          extend it on the <Link to="/settings">Settings</Link> page before it runs out.
        </AlertBanner>
      )}

      {latest ? (
        <p>Last synced at: {formatTimestamp(latest.syncedAt)}</p>
      ) : (
        <AlertBanner kind="info">
          No sync data yet. <Link to="/sync">Go to Sync</Link> to pull your first snapshot.
        </AlertBanner>
      )}

      <hr />

      <div className="nav-grid">
        <NavCard to="/dashboard" title="Dashboard" caption="KPIs, cashflow-by-category, networth breakdown, and the raw snapshot table." />
        <NavCard to="/sync" title="Sync" caption="Pull fresh data from the Torn API and review auto-categorized log entries." />
        <NavCard to="/checklist" title="Checklist" caption="Recurring and one-off tasks — daily refills, war prep, and more." />
        <NavCard
          to="/categories"
          title="Categories"
          premium={!premium?.isPremium}
          caption="Manage categories and bulk-recategorize log entries by title."
        />
        <NavCard to="/settings" title="Settings" caption="API key, War Mode toggle, and your Premium/License status." />
      </div>

      <footer className="page-footer">
        <p>
          Free tier covers day-to-day tracking. Premium (full history sync, Categories, and
          automatic checklist resets) unlocks with a 7-day free trial or by sending Xanax in-game —
          see Settings.
        </p>
        <p>
          This app is fully open source —{' '}
          <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer">
            read the code on GitHub
          </a>
          . Not affiliated with or endorsed by Torn. See Settings for what data is accessed/stored
          and how to remove it.
        </p>
        <p>
          Feedback or suggestions? Send a Torn message to{' '}
          <a href={DEV_PROFILE_URL} target="_blank" rel="noreferrer">
            {DEV_PROFILE_LABEL}
          </a>{' '}
          — see Settings.
        </p>
      </footer>
    </div>
  );
}
```

- [ ] **Step 3: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 4: Manually verify in the browser**

```bash
cd frontend && npm run dev
```
(`.env` from Task 7 already has `VITE_USE_MOCKS=true`.) Log in via the mock Login page, confirm the
Home page shows: the "Signed in as MockPlayer" banner, "Last synced at" line (the mock has
snapshots), all five nav cards (Categories shows a Premium badge only if you edit
`mockPremium.isPremium` to `false` in `src/mocks/data.ts` and reload — revert after checking), and
the footer with working GitHub/dev-profile links (`target="_blank"`, don't need to click through).

- [ ] **Step 5: Commit**

```bash
cd frontend
git add src/components/layout/NavCard.tsx src/pages/Home.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add Home page"
```

---

### Task 9: Dashboard page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx` (replaces Task 7's placeholder)
- Modify: `frontend/package.json` (add `recharts` — already listed in Task 1, just confirming it's installed/used here)

**Interfaces:**
- Consumes: `getDashboard` (Task 4), `getSnapshots` (Task 4), `resolveTimeRange`/`TimeRangePreset`
  (Task 5), `snapshotsToCsv`/`downloadCsv` (Task 5), `formatCurrency`/`formatTimestamp` (Task 2),
  `KpiCard`/`SectionHeading`/`AlertBanner`/`Button` (Task 2), `SnapshotDTO` (Task 3).

- [ ] **Step 1: Write `frontend/src/pages/Dashboard.tsx`**

```tsx
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getDashboard } from '../api/dashboard';
import { getSnapshots } from '../api/snapshots';
import KpiCard from '../components/ui/KpiCard';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import { formatCurrency, formatTimestamp } from '../lib/format';
import { resolveTimeRange, type TimeRangePreset } from '../lib/dateRange';
import { snapshotsToCsv, downloadCsv } from '../lib/csv';
import type { SnapshotDTO } from '../types/api';

const PRESETS: { value: TimeRangePreset; label: string }[] = [
  { value: 'last7', label: 'Last 7 days' },
  { value: 'last30', label: 'Last 30 days' },
  { value: 'last90', label: 'Last 90 days' },
  { value: 'custom', label: 'Custom' },
  { value: 'all', label: 'All time' },
];

function toDateInputValue(ts: number): string {
  return new Date(ts * 1000).toISOString().slice(0, 10);
}

function fromDateInputValue(value: string, endOfDay: boolean): number {
  const ms = Date.parse(`${value}T${endOfDay ? '23:59:59' : '00:00:00'}Z`);
  return Math.floor(ms / 1000);
}

const chartTooltipStyle = { background: 'var(--panel-2)', border: '1px solid var(--line-lit)' };

export default function DashboardPage() {
  const [preset, setPreset] = useState<TimeRangePreset>('last30');
  const [customStart, setCustomStart] = useState<string | null>(null);
  const [customEnd, setCustomEnd] = useState<string | null>(null);
  const [tab, setTab] = useState<'cashflow' | 'networth'>('cashflow');

  const boundsQuery = useQuery({ queryKey: ['snapshots', 'all'], queryFn: () => getSnapshots() });
  const snapshots = boundsQuery.data?.snapshots ?? [];

  const bounds = useMemo(() => {
    if (snapshots.length === 0) return null;
    return { minTs: snapshots[0].syncedAt, maxTs: snapshots[snapshots.length - 1].syncedAt };
  }, [snapshots]);

  const range = useMemo(() => {
    if (!bounds) return null;
    if (preset === 'custom') {
      if (!customStart || !customEnd) return null;
      return resolveTimeRange('custom', bounds, {
        startTs: fromDateInputValue(customStart, false),
        endTs: fromDateInputValue(customEnd, true),
      });
    }
    return resolveTimeRange(preset, bounds);
  }, [preset, bounds, customStart, customEnd]);

  const dashboardQuery = useQuery({
    queryKey: ['dashboard', range?.startTs, range?.endTs],
    queryFn: () => getDashboard(range!.startTs, range!.endTs),
    enabled: range !== null,
  });

  if (boundsQuery.isLoading) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        <p>Loading…</p>
      </div>
    );
  }

  if (snapshots.length === 0) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        <AlertBanner kind="info">Need at least one synced snapshot. Go to Sync first.</AlertBanner>
      </div>
    );
  }

  const dashboard = dashboardQuery.data;
  const snapshotColumns = dashboard && dashboard.snapshots.length > 0 ? (Object.keys(dashboard.snapshots[0]) as (keyof SnapshotDTO)[]) : [];

  return (
    <div className="page">
      <h1>Dashboard</h1>

      <div className="tabs" role="tablist" aria-label="Time range">
        {PRESETS.map((p) => (
          <button key={p.value} className={preset === p.value ? 'active' : ''} onClick={() => setPreset(p.value)}>
            {p.label}
          </button>
        ))}
      </div>

      {preset === 'custom' && bounds && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div>
            <label htmlFor="custom-start">Start date</label>
            <input
              id="custom-start"
              type="date"
              min={toDateInputValue(bounds.minTs)}
              max={toDateInputValue(bounds.maxTs)}
              value={customStart ?? toDateInputValue(bounds.minTs)}
              onChange={(e) => setCustomStart(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="custom-end">End date</label>
            <input
              id="custom-end"
              type="date"
              min={toDateInputValue(bounds.minTs)}
              max={toDateInputValue(bounds.maxTs)}
              value={customEnd ?? toDateInputValue(bounds.maxTs)}
              onChange={(e) => setCustomEnd(e.target.value)}
            />
          </div>
        </div>
      )}

      {!dashboard ? (
        <p>Loading…</p>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
            <KpiCard label="Total Cashflow" value={formatCurrency(dashboard.cashflowTotal)} />
            <KpiCard label="Cashflow / Day" value={formatCurrency(dashboard.cashflowPerDay)} />
          </div>

          <hr />
          <SectionHeading>Cashflow by Category</SectionHeading>
          {dashboard.categoryBreakdown.length === 0 ? (
            <AlertBanner kind="info">No categorized log data in this range yet.</AlertBanner>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(200, dashboard.categoryBreakdown.length * 36)}>
              <BarChart data={[...dashboard.categoryBreakdown].sort((a, b) => a.amount - b.amount)} layout="vertical">
                <CartesianGrid stroke="var(--line)" horizontal={false} />
                <XAxis type="number" stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                <YAxis type="category" dataKey="category" stroke="var(--text-mute)" width={140} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} />
                <Bar dataKey="amount">
                  {dashboard.categoryBreakdown.map((row) => (
                    <Cell key={row.category} fill={row.amount >= 0 ? 'var(--gold)' : 'var(--red)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}

          <hr />
          <SectionHeading>Networth Breakdown</SectionHeading>
          <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
            As of the latest sync in the selected time range. "Trade" isn't exposed by the Torn API
            and is shown as n/a. This reflects Torn's own networth figure, which Torn recalculates
            roughly once a day — not a live estimate, so it can lag behind other tools that compute
            it more frequently.
          </p>
          <table>
            <thead>
              <tr>
                <th>Component</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.networthBreakdown.map((row) => (
                <tr key={row.component}>
                  <td>{row.component}</td>
                  <td>{formatCurrency(row.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <hr />
          <SectionHeading>Time Series</SectionHeading>
          <div className="tabs">
            <button className={tab === 'cashflow' ? 'active' : ''} onClick={() => setTab('cashflow')}>
              Cashflow / Day
            </button>
            <button className={tab === 'networth' ? 'active' : ''} onClick={() => setTab('networth')}>
              Networth
            </button>
          </div>
          {tab === 'cashflow' ? (
            dashboard.dailyCashflow.length === 0 ? (
              <AlertBanner kind="info">No categorized cashflow entries in this range yet.</AlertBanner>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dashboard.dailyCashflow}>
                  <CartesianGrid stroke="var(--line)" />
                  <XAxis dataKey="date" stroke="var(--text-mute)" />
                  <YAxis stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                  <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} />
                  <Bar dataKey="cashflowDelta" fill="var(--gold)" />
                </BarChart>
              </ResponsiveContainer>
            )
          ) : dashboard.dailyNetworth.length === 0 ? (
            <AlertBanner kind="info">No synced data in this range yet.</AlertBanner>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={dashboard.dailyNetworth}>
                <CartesianGrid stroke="var(--line)" />
                <XAxis dataKey="date" stroke="var(--text-mute)" />
                <YAxis stroke="var(--text-mute)" tickFormatter={(v: number) => formatCurrency(v)} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} contentStyle={chartTooltipStyle} />
                <Line type="monotone" dataKey="networth" stroke="var(--gold-bright)" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}

          <hr />
          <SectionHeading>Raw Snapshots</SectionHeading>
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  {snapshotColumns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dashboard.snapshots.map((s) => (
                  <tr key={s.id}>
                    {snapshotColumns.map((c) => (
                      <td key={c}>{c === 'syncedAt' ? formatTimestamp(s.syncedAt) : String(s[c] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 12 }}>
            <Button onClick={() => downloadCsv('torn_snapshots.csv', snapshotsToCsv(dashboard.snapshots))}>Export CSV</Button>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 3: Manually verify in the browser**

```bash
cd frontend && npm run dev
```
Log in, go to Dashboard. Confirm: both KPI cards render with formatted dollar amounts, the
category bar chart renders with gold/red bars matching sign, the networth table shows 20 rows
including "Trade" as `n/a`, both Time Series tabs render (bar for cashflow, line for networth),
switching to "Custom" shows two date pickers and updates the charts, "Export CSV" downloads a file
(check the browser's download prompt/notification).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/Dashboard.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add Dashboard page"
```

---

### Task 10: Sync page

**Files:**
- Modify: `frontend/src/pages/Sync.tsx` (replaces Task 7's placeholder)

**Interfaces:**
- Consumes: `useAuth()` (Task 7); `syncIncremental`, `startFullHistorySync`, `getFullHistoryJob`
  (Task 4 `sync.ts`); `getLatestSnapshot`, `updateSnapshotNote` (Task 4 `snapshots.ts`);
  `getUncategorizedEntries`, `getIgnoredEntries`, `updateLogEntry`, `ignoreLogEntry`,
  `restoreLogEntry` (Task 4 `logEntries.ts`); `getCategories` (Task 4 `categories.ts`);
  `clearAllData` (Task 4 `data.ts`); `ApiError` (Task 3); UI primitives (Task 2).
- Produces: a local `useFullHistoryJob(jobId)` hook (polls every 2.5s while `status === 'running'`,
  exposes `isStalled` when no progress for 60s) — local to this file, not reused elsewhere.

- [ ] **Step 1: Write `frontend/src/pages/Sync.tsx`**

```tsx
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { syncIncremental, startFullHistorySync, getFullHistoryJob } from '../api/sync';
import { getLatestSnapshot, updateSnapshotNote } from '../api/snapshots';
import { getUncategorizedEntries, getIgnoredEntries, updateLogEntry, ignoreLogEntry, restoreLogEntry } from '../api/logEntries';
import { getCategories } from '../api/categories';
import { clearAllData } from '../api/data';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { formatTimestamp, formatCurrency } from '../lib/format';
import type { LogEntryDTO } from '../types/api';

function useFullHistoryJob(jobId: number | null) {
  const [lastProgressKey, setLastProgressKey] = useState('');
  const [lastProgressAt, setLastProgressAt] = useState(Date.now());

  const query = useQuery({
    queryKey: ['syncJob', jobId],
    queryFn: () => getFullHistoryJob(jobId as number),
    enabled: jobId !== null,
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 2500 : false),
  });

  useEffect(() => {
    if (!query.data) return;
    const key = `${query.data.pagesFetched}-${query.data.entriesFetched}`;
    if (key !== lastProgressKey) {
      setLastProgressKey(key);
      setLastProgressAt(Date.now());
    }
  }, [query.data, lastProgressKey]);

  const isStalled = query.data?.status === 'running' && Date.now() - lastProgressAt > 60000;
  return { ...query, isStalled };
}

export default function SyncPage() {
  const { premium } = useAuth();
  const queryClient = useQueryClient();

  const incrementalMutation = useMutation({
    mutationFn: syncIncremental,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
    },
  });

  const [fullHistoryJobId, setFullHistoryJobId] = useState<number | null>(null);
  const [attemptedWithoutPremium, setAttemptedWithoutPremium] = useState(false);
  const startFullHistoryMutation = useMutation({
    mutationFn: startFullHistorySync,
    onSuccess: (data) => setFullHistoryJobId(data.jobId),
  });
  const fullHistoryJob = useFullHistoryJob(fullHistoryJobId);

  useEffect(() => {
    if (fullHistoryJob.data?.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['snapshots'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
    }
  }, [fullHistoryJob.data?.status, queryClient]);

  const latestSnapshotQuery = useQuery({ queryKey: ['snapshots', 'latest'], queryFn: getLatestSnapshot });
  const latest = latestSnapshotQuery.data?.snapshot ?? null;
  const [noteDraft, setNoteDraft] = useState<string | null>(null);
  const noteMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => updateSnapshotNote(id, note),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['snapshots'] }),
  });

  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories });
  const categoryOptions = [...(categoriesQuery.data?.categories.map((c) => c.name) ?? []), 'Uncategorized'];

  const uncategorizedQuery = useQuery({ queryKey: ['log-entries', 'uncategorized'], queryFn: () => getUncategorizedEntries(25) });
  const ignoredQuery = useQuery({ queryKey: ['log-entries', 'ignored'], queryFn: () => getIgnoredEntries(25) });

  const saveEntryMutation = useMutation({
    mutationFn: ({ id, category, note }: { id: number; category: string; note: string }) => updateLogEntry(id, category, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
  const ignoreEntryMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note: string }) => ignoreLogEntry(id, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
  });
  const restoreEntryMutation = useMutation({
    mutationFn: (id: number) => restoreLogEntry(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['log-entries'] }),
  });

  const [confirmClear, setConfirmClear] = useState(false);
  const clearMutation = useMutation({
    mutationFn: clearAllData,
    onSuccess: () => {
      setConfirmClear(false);
      queryClient.invalidateQueries();
    },
  });

  return (
    <div className="page">
      <h1>Sync</h1>

      {latest ? <p>Last sync: {formatTimestamp(latest.syncedAt)}</p> : <p>No sync has happened yet.</p>}

      <div style={{ margin: '16px 0' }}>
        <Button variant="primary" onClick={() => incrementalMutation.mutate()} disabled={incrementalMutation.isPending}>
          {incrementalMutation.isPending ? 'Syncing…' : 'Sync now'}
        </Button>
      </div>

      {incrementalMutation.isSuccess && (
        <AlertBanner kind="success">
          Sync complete. Stored 1 snapshot and {incrementalMutation.data.logEntriesStored} log entries.
          {incrementalMutation.data.paymentMessage && <> {incrementalMutation.data.paymentMessage}</>}
        </AlertBanner>
      )}
      {incrementalMutation.isError && (
        <AlertBanner kind="error">
          {incrementalMutation.error instanceof ApiError ? incrementalMutation.error.message : 'Sync failed.'}
        </AlertBanner>
      )}

      <hr />
      <SectionHeading premium>Full History Sync</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Fetches your current bars/money/stats plus your complete log history by paging backward
        through the Torn API, bypassing its ~100-entries-per-call cap. This uses many API requests
        and can take a while for accounts with a long history.
      </p>
      {!premium?.isPremium && (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
          Requires Premium — clicking below will show your options (trial, Xanax payment, or faction bulk).
        </p>
      )}

      <Button
        onClick={() => {
          if (!premium?.isPremium) {
            setAttemptedWithoutPremium(true);
            return;
          }
          startFullHistoryMutation.mutate();
        }}
        disabled={startFullHistoryMutation.isPending || fullHistoryJob.data?.status === 'running'}
      >
        Get all Data
      </Button>

      {attemptedWithoutPremium && !premium?.isPremium && (
        <AlertBanner kind="warning">
          Full History Sync is a Premium feature. Start your free trial, pay with Xanax, or check
          faction options on the Settings page.
        </AlertBanner>
      )}

      {fullHistoryJobId !== null && fullHistoryJob.data && (
        <AlertBanner kind={fullHistoryJob.data.status === 'failed' ? 'error' : 'info'}>
          {fullHistoryJob.data.status === 'running' && (
            <>
              Page {fullHistoryJob.data.pagesFetched}: {fullHistoryJob.data.entriesFetched} log entries
              fetched so far
              {fullHistoryJob.data.oldestTimestamp && ` (oldest so far: ${formatTimestamp(fullHistoryJob.data.oldestTimestamp)})`}…
              {fullHistoryJob.isStalled && ' This looks stalled — you can retry below.'}
            </>
          )}
          {fullHistoryJob.data.status === 'completed' && fullHistoryJob.data.result && (
            <>
              Full history sync complete. {fullHistoryJob.data.result.newEntriesStored} new log
              entries ({fullHistoryJob.data.result.alreadyStored} were already stored).
            </>
          )}
          {fullHistoryJob.data.status === 'failed' && <>Full history sync failed: {fullHistoryJob.data.error}</>}
        </AlertBanner>
      )}
      {fullHistoryJob.isStalled && <Button onClick={() => startFullHistoryMutation.mutate()}>Retry</Button>}

      <hr />
      <SectionHeading>Period Note</SectionHeading>
      {latest && (
        <div style={{ maxWidth: 480 }}>
          <label htmlFor="period-note">Note for the latest sync period</label>
          <textarea id="period-note" value={noteDraft ?? latest.note ?? ''} onChange={(e) => setNoteDraft(e.target.value)} rows={3} />
          <div style={{ marginTop: 8 }}>
            <Button
              onClick={() => noteMutation.mutate({ id: latest.id, note: noteDraft ?? latest.note ?? '' })}
              disabled={noteMutation.isPending}
            >
              Save note
            </Button>
          </div>
          {noteMutation.isSuccess && <AlertBanner kind="success">Note saved.</AlertBanner>}
        </div>
      )}

      <hr />
      <SectionHeading>Uncategorized Log Entries</SectionHeading>
      {!uncategorizedQuery.data || uncategorizedQuery.data.entries.length === 0 ? (
        <AlertBanner kind="info">No uncategorized log entries.</AlertBanner>
      ) : (
        <>
          {uncategorizedQuery.data.totalCount > uncategorizedQuery.data.entries.length && (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
              Showing the {uncategorizedQuery.data.entries.length} most recent of{' '}
              {uncategorizedQuery.data.totalCount} uncategorized entries. Use the Categories page to
              bulk-recategorize the rest by title.
            </p>
          )}
          {uncategorizedQuery.data.entries.map((entry) => (
            <UncategorizedEntryRow
              key={entry.id}
              entry={entry}
              categoryOptions={categoryOptions}
              onSave={(category, note) => saveEntryMutation.mutate({ id: entry.id, category, note })}
              onIgnore={(note) => ignoreEntryMutation.mutate({ id: entry.id, note })}
            />
          ))}
        </>
      )}

      <hr />
      <SectionHeading>Ignored Log Entries</SectionHeading>
      {!ignoredQuery.data || ignoredQuery.data.entries.length === 0 ? (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>No ignored log entries.</p>
      ) : (
        <details>
          <summary>
            {ignoredQuery.data.entries.length} most recent of {ignoredQuery.data.totalCount} ignored entries
          </summary>
          {ignoredQuery.data.entries.map((entry) => (
            <div key={entry.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0' }}>
              <span>
                <strong>{entry.title || 'Unknown event'}</strong> — {formatTimestamp(entry.timestamp)}
              </span>
              <Button onClick={() => restoreEntryMutation.mutate(entry.id)}>Restore</Button>
            </div>
          ))}
        </details>
      )}

      <hr />
      <SectionHeading>Danger Zone</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Deletes all your synced snapshots, log entries, and learned category rules from the
        database. Your checklist tasks and War Mode setting are not affected. This cannot be
        undone.
      </p>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, textTransform: 'none' }}>
        <input type="checkbox" style={{ width: 'auto' }} checked={confirmClear} onChange={(e) => setConfirmClear(e.target.checked)} />
        I understand this permanently deletes all synced data
      </label>
      <div style={{ marginTop: 8 }}>
        <Button variant="danger" disabled={!confirmClear || clearMutation.isPending} onClick={() => clearMutation.mutate()}>
          Clear DB
        </Button>
      </div>
      {clearMutation.isSuccess && <AlertBanner kind="success">All synced data cleared.</AlertBanner>}
    </div>
  );
}

function UncategorizedEntryRow({
  entry,
  categoryOptions,
  onSave,
  onIgnore,
}: {
  entry: LogEntryDTO;
  categoryOptions: string[];
  onSave: (category: string, note: string) => void;
  onIgnore: (note: string) => void;
}) {
  const [category, setCategory] = useState('Uncategorized');
  const [note, setNote] = useState(entry.userNote ?? '');

  return (
    <Card>
      <p>
        <strong>{entry.title || 'Unknown event'}</strong> — {formatTimestamp(entry.timestamp)} —{' '}
        {entry.amount !== null ? formatCurrency(entry.amount) : 'no amount detected'}
      </p>
      {entry.rawText && <p style={{ color: 'var(--text-dim)', fontSize: 12 }}>{entry.rawText}</p>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div style={{ flex: '1 1 160px' }}>
          <label htmlFor={`cat-${entry.id}`}>Category</label>
          <select id={`cat-${entry.id}`} value={category} onChange={(e) => setCategory(e.target.value)}>
            {categoryOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: '1 1 160px' }}>
          <label htmlFor={`note-${entry.id}`}>Note</label>
          <input id={`note-${entry.id}`} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <Button onClick={() => onSave(category, note)}>Save</Button>
        <Button onClick={() => onIgnore(note)}>Ignore</Button>
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 3: Manually verify in the browser**

```bash
cd frontend && npm run dev
```
Log in, go to Sync. Confirm: "Sync now" shows a success banner with the stored counts (the mock
adds 1 snapshot + 1 entry); "Get all Data" (mock player is Premium) starts a job and the progress
banner updates every ~1.2s through 4 ticks before showing "complete"; the Period Note textarea
saves and shows a success banner; the Uncategorized section shows the mock's uncategorized entry
with working Category/Note/Save/Ignore (after Save/Ignore, the entry disappears from the list);
the Ignored section is an expandable `<details>` with a working Restore button; the Danger Zone's
"Clear DB" button stays disabled until the checkbox is checked, then clears (Dashboard should show
"need at least one snapshot" afterward).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/Sync.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add Sync page"
```

---

### Task 11: Checklist page

**Files:**
- Modify: `frontend/src/pages/Checklist.tsx` (replaces Task 7's placeholder)

**Interfaces:**
- Consumes: `useAuth()` (Task 7); `getChecklist`, `createTask`, `updateTask`, `deleteTask`,
  `setTaskDone`, `ChecklistTaskInput` (Task 4 `checklist.ts`); `getWarMode` (Task 4 `settings.ts`);
  UI primitives (Task 2); `ChecklistTaskDTO`/`RepeatType` (Task 3).

- [ ] **Step 1: Write `frontend/src/pages/Checklist.tsx`**

```tsx
import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getChecklist, createTask, updateTask, deleteTask, setTaskDone, type ChecklistTaskInput } from '../api/checklist';
import { getWarMode } from '../api/settings';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import type { ChecklistTaskDTO, RepeatType } from '../types/api';

const REPEAT_TYPE_LABELS: Record<RepeatType, string> = {
  daily: 'Daily',
  weekly: 'Weekly',
  every_x_days: 'Every X Days',
  once: 'One-off',
  war_day: 'On War Days',
};

const REPEAT_TYPE_ORDER: RepeatType[] = ['daily', 'weekly', 'every_x_days', 'war_day', 'once'];

export default function ChecklistPage() {
  const { premium } = useAuth();
  const queryClient = useQueryClient();

  const tasksQuery = useQuery({ queryKey: ['checklist'], queryFn: getChecklist });
  const warModeQuery = useQuery({ queryKey: ['warMode'], queryFn: getWarMode });

  const invalidateTasks = () => queryClient.invalidateQueries({ queryKey: ['checklist'] });

  const createMutation = useMutation({ mutationFn: createTask, onSuccess: invalidateTasks });
  const updateMutation = useMutation({
    mutationFn: ({ id, input }: { id: number; input: ChecklistTaskInput }) => updateTask(id, input),
    onSuccess: invalidateTasks,
  });
  const deleteMutation = useMutation({ mutationFn: deleteTask, onSuccess: invalidateTasks });
  const doneMutation = useMutation({
    mutationFn: ({ id, done }: { id: number; done: boolean }) => setTaskDone(id, done),
    onSuccess: invalidateTasks,
  });

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [repeatType, setRepeatType] = useState<RepeatType>('daily');
  const [intervalDays, setIntervalDays] = useState(2);
  const [editingId, setEditingId] = useState<number | null>(null);

  function handleAddTask(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    createMutation.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        repeatType,
        repeatIntervalDays: repeatType === 'every_x_days' ? intervalDays : null,
      },
      { onSuccess: () => { setTitle(''); setDescription(''); setRepeatType('daily'); } },
    );
  }

  const warModeActive = warModeQuery.data?.active ?? false;
  const allTasks = tasksQuery.data?.tasks ?? [];
  const visibleTasks = allTasks.filter((t) => t.repeatType !== 'war_day' || warModeActive);
  const openTasks = visibleTasks.filter((t) => !t.isDoneCurrentCycle);
  const doneTasks = visibleTasks.filter((t) => t.isDoneCurrentCycle);

  const grouped = new Map<RepeatType, ChecklistTaskDTO[]>();
  for (const rt of REPEAT_TYPE_ORDER) {
    const group = openTasks.filter((t) => t.repeatType === rt);
    if (group.length > 0) grouped.set(rt, group);
  }

  return (
    <div className="page">
      <h1>Checklist</h1>

      {!premium?.isPremium && (
        <AlertBanner kind="info">
          Recurring tasks reset automatically with Premium. On the free tier, check tasks off and
          un-check them yourself when a new cycle starts.
        </AlertBanner>
      )}

      <SectionHeading>Add a task</SectionHeading>
      <Card>
        <form onSubmit={handleAddTask}>
          <label htmlFor="task-title">Title</label>
          <input id="task-title" value={title} onChange={(e) => setTitle(e.target.value)} />

          <label htmlFor="task-description" style={{ marginTop: 8 }}>
            Description (optional)
          </label>
          <textarea id="task-description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />

          <label htmlFor="task-repeat" style={{ marginTop: 8 }}>
            Repeat type
          </label>
          <select id="task-repeat" value={repeatType} onChange={(e) => setRepeatType(e.target.value as RepeatType)}>
            {REPEAT_TYPE_ORDER.map((rt) => (
              <option key={rt} value={rt}>
                {REPEAT_TYPE_LABELS[rt]}
              </option>
            ))}
          </select>

          {repeatType === 'every_x_days' && (
            <>
              <label htmlFor="task-interval" style={{ marginTop: 8 }}>
                Every X days
              </label>
              <input id="task-interval" type="number" min={1} value={intervalDays} onChange={(e) => setIntervalDays(Number(e.target.value))} />
            </>
          )}

          <div style={{ marginTop: 12 }}>
            <Button type="submit" variant="primary" disabled={createMutation.isPending || !title.trim()}>
              Add task
            </Button>
          </div>
        </form>
      </Card>

      <hr />
      <SectionHeading>Open Tasks</SectionHeading>
      {openTasks.length === 0 ? (
        <AlertBanner kind="info">Nothing open right now.</AlertBanner>
      ) : (
        [...grouped.entries()].map(([rt, group]) => (
          <div key={rt}>
            <p style={{ fontFamily: 'var(--label)', textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 12, color: 'var(--text-mute)' }}>
              {REPEAT_TYPE_LABELS[rt]}
            </p>
            {group.map((task) =>
              editingId === task.id ? (
                <EditTaskForm
                  key={task.id}
                  task={task}
                  onCancel={() => setEditingId(null)}
                  onSave={(input) => {
                    updateMutation.mutate({ id: task.id, input });
                    setEditingId(null);
                  }}
                />
              ) : (
                <TaskRow
                  key={task.id}
                  task={task}
                  onToggleDone={() => doneMutation.mutate({ id: task.id, done: true })}
                  onEdit={() => setEditingId(task.id)}
                  onDelete={() => deleteMutation.mutate(task.id)}
                />
              ),
            )}
          </div>
        ))
      )}

      <hr />
      <SectionHeading>Completed</SectionHeading>
      {doneTasks.length === 0 ? (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Nothing completed for the current cycle.</p>
      ) : (
        <details>
          <summary>{doneTasks.length} completed task(s)</summary>
          {doneTasks.map((task) => (
            <div key={task.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0' }}>
              <input type="checkbox" style={{ width: 'auto' }} checked onChange={() => doneMutation.mutate({ id: task.id, done: false })} />
              <span style={{ textDecoration: 'line-through' }}>{task.title}</span>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

function TaskRow({
  task,
  onToggleDone,
  onEdit,
  onDelete,
}: {
  task: ChecklistTaskDTO;
  onToggleDone: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <input type="checkbox" style={{ width: 'auto', marginTop: 4 }} checked={false} onChange={onToggleDone} />
        <div style={{ flex: 1 }}>
          <strong>{task.title}</strong>
          {task.description && <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>{task.description}</p>}
        </div>
        <Button onClick={onEdit}>Edit</Button>
        <Button variant="danger" onClick={onDelete}>
          Delete
        </Button>
      </div>
    </Card>
  );
}

function EditTaskForm({
  task,
  onCancel,
  onSave,
}: {
  task: ChecklistTaskDTO;
  onCancel: () => void;
  onSave: (input: ChecklistTaskInput) => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? '');
  const [repeatType, setRepeatType] = useState<RepeatType>(task.repeatType);
  const [intervalDays, setIntervalDays] = useState(task.repeatIntervalDays ?? 2);

  return (
    <Card>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave({
            title: title.trim(),
            description: description.trim(),
            repeatType,
            repeatIntervalDays: repeatType === 'every_x_days' ? intervalDays : null,
          });
        }}
      >
        <label htmlFor={`edit-title-${task.id}`}>Title</label>
        <input id={`edit-title-${task.id}`} value={title} onChange={(e) => setTitle(e.target.value)} />

        <label htmlFor={`edit-desc-${task.id}`} style={{ marginTop: 8 }}>
          Description
        </label>
        <textarea id={`edit-desc-${task.id}`} value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />

        <label htmlFor={`edit-repeat-${task.id}`} style={{ marginTop: 8 }}>
          Repeat type
        </label>
        <select id={`edit-repeat-${task.id}`} value={repeatType} onChange={(e) => setRepeatType(e.target.value as RepeatType)}>
          {REPEAT_TYPE_ORDER.map((rt) => (
            <option key={rt} value={rt}>
              {REPEAT_TYPE_LABELS[rt]}
            </option>
          ))}
        </select>

        {repeatType === 'every_x_days' && (
          <>
            <label htmlFor={`edit-interval-${task.id}`} style={{ marginTop: 8 }}>
              Every X days
            </label>
            <input
              id={`edit-interval-${task.id}`}
              type="number"
              min={1}
              value={intervalDays}
              onChange={(e) => setIntervalDays(Number(e.target.value))}
            />
          </>
        )}

        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <Button type="submit" variant="primary">
            Save changes
          </Button>
          <Button type="button" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
```

- [ ] **Step 2: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 3: Manually verify in the browser**

```bash
cd frontend && npm run dev
```
Log in, go to Checklist. Confirm: adding a task with "Every X Days" shows the interval input and
the new task appears grouped correctly; checking a task's Done checkbox moves it into the
collapsed Completed section; un-checking it in Completed moves it back to Open; Edit shows the
inline form pre-filled and Save updates the task; Delete removes it; the "Rotate war targets"
(`war_day`) mock task is hidden until you flip `mockWarMode.active = true` in
`src/mocks/data.ts` and reload (revert after checking).

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/Checklist.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add Checklist page"
```

---

### Task 12: Settings page

**Files:**
- Modify: `frontend/src/pages/Settings.tsx` (replaces Task 7's placeholder)

**Interfaces:**
- Consumes: `useAuth()`/`useInvalidateAuth()` (Task 7); `login`, `logout` (Task 4 `auth.ts`);
  `getWarMode`, `setWarMode` (Task 4 `settings.ts`); `getLicensingStatus`, `startTrial`,
  `scanPayment`, `getFactionPreview`, `scanGroupPayment` (Task 4 `licensing.ts`);
  `getLifetimeGrants`, `createLifetimeGrant`, `deleteLifetimeGrant` (Task 4 `admin.ts`); `ApiError`
  (Task 3); UI primitives (Task 2); `API_KEY_CREATE_URL`/`DEV_PROFILE_URL`/`DEV_PROFILE_LABEL`/
  `GITHUB_REPO_URL` (Task 7 `constants.ts`); `GrantScope` (Task 3).

- [ ] **Step 1: Write `frontend/src/pages/Settings.tsx`**

```tsx
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth, useInvalidateAuth } from '../hooks/useAuth';
import { login, logout } from '../api/auth';
import { getWarMode, setWarMode } from '../api/settings';
import { getLicensingStatus, startTrial, scanPayment, getFactionPreview, scanGroupPayment } from '../api/licensing';
import { getLifetimeGrants, createLifetimeGrant, deleteLifetimeGrant } from '../api/admin';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { formatTimestamp, formatDays } from '../lib/format';
import { API_KEY_CREATE_URL, DEV_PROFILE_URL, DEV_PROFILE_LABEL, GITHUB_REPO_URL } from '../constants';
import type { GrantScope } from '../types/api';

const SOURCE_LABELS: Record<string, string> = {
  trial: 'your free trial',
  individual: 'your payment',
  faction: 'your faction',
  lifetimeIndividual: 'a lifetime grant',
  lifetimeFaction: "your faction's lifetime grant",
};

export default function SettingsPage() {
  const { player, premium } = useAuth();
  const invalidateAuth = useInvalidateAuth();
  const queryClient = useQueryClient();

  const [apiKeyInput, setApiKeyInput] = useState('');
  const reKeyMutation = useMutation({
    mutationFn: () => login(apiKeyInput.trim()),
    onSuccess: () => {
      invalidateAuth();
      setApiKeyInput('');
    },
  });
  const logoutMutation = useMutation({ mutationFn: logout, onSuccess: () => invalidateAuth() });

  const warModeQuery = useQuery({ queryKey: ['warMode'], queryFn: getWarMode });
  const warModeMutation = useMutation({
    mutationFn: setWarMode,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['warMode'] }),
  });

  const licensingQuery = useQuery({ queryKey: ['licensing', 'status'], queryFn: getLicensingStatus });
  const trialMutation = useMutation({
    mutationFn: startTrial,
    onSuccess: () => {
      invalidateAuth();
      queryClient.invalidateQueries({ queryKey: ['licensing'] });
    },
  });

  const [payMode, setPayMode] = useState<'individual' | 'faction'>('individual');
  const factionPreviewQuery = useQuery({
    queryKey: ['licensing', 'factionPreview'],
    queryFn: getFactionPreview,
    enabled: payMode === 'faction' && !!player?.factionId,
  });
  const scanPaymentMutation = useMutation({
    mutationFn: () => scanPayment(),
    onSuccess: () => {
      invalidateAuth();
      queryClient.invalidateQueries({ queryKey: ['licensing'] });
    },
  });
  const scanGroupPaymentMutation = useMutation({
    mutationFn: () => scanGroupPayment(),
    onSuccess: () => {
      invalidateAuth();
      queryClient.invalidateQueries({ queryKey: ['licensing'] });
    },
  });

  const grantsQuery = useQuery({ queryKey: ['admin', 'grants'], queryFn: getLifetimeGrants, enabled: !!player?.isAdmin });
  const [grantScope, setGrantScope] = useState<GrantScope>('individual');
  const [grantKey, setGrantKey] = useState('');
  const createGrantMutation = useMutation({
    mutationFn: () => createLifetimeGrant(grantScope, Number(grantKey)),
    onSuccess: () => {
      setGrantKey('');
      queryClient.invalidateQueries({ queryKey: ['admin', 'grants'] });
    },
  });
  const revokeGrantMutation = useMutation({
    mutationFn: ({ scope, key }: { scope: GrantScope; key: number }) => deleteLifetimeGrant(scope, key),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'grants'] }),
  });

  if (!player || !premium) return null;

  return (
    <div className="page">
      <h1>Settings</h1>

      <SectionHeading>Torn API Key</SectionHeading>
      <p>
        <a href={API_KEY_CREATE_URL} target="_blank" rel="noreferrer">
          Click here to create a scoped API key
        </a>{' '}
        — this opens Torn's own key creation page with exactly the permissions this app needs
        pre-checked, nothing more. No blanket Full Access required.
      </p>
      <details>
        <summary>What does this app access, and why?</summary>
        <ul>
          <li>
            <strong>Basic profile</strong> — your name and faction, so your data is scoped to your account.
          </li>
          <li>
            <strong>Bars</strong> — energy/nerve/happy, for the Dashboard KPIs.
          </li>
          <li>
            <strong>Money</strong> — cash on hand, vault, and bank, for cashflow tracking.
          </li>
          <li>
            <strong>Personal stats</strong> — net worth and its breakdown.
          </li>
          <li>
            <strong>Log</strong> — your activity log, used to build categorized cashflow history and to detect Xanax payments for Premium.
          </li>
        </ul>
        <p>
          That's the complete list — nothing is ever written back to Torn through this key, it's
          used read-only. The key itself is remembered only via your browser's session cookie,
          never written to a shared file, and never logged.
        </p>
      </details>

      <p>
        Signed in as <strong>{player.name}</strong> (player id {player.playerId}), key <code>{player.maskedApiKey}</code>.
      </p>

      <Card>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            reKeyMutation.mutate();
          }}
        >
          <label htmlFor="settings-api-key">Torn API key</label>
          <input id="settings-api-key" type="password" value={apiKeyInput} onChange={(e) => setApiKeyInput(e.target.value)} autoComplete="off" />
          <div style={{ marginTop: 8 }}>
            <Button type="submit" disabled={!apiKeyInput.trim() || reKeyMutation.isPending}>
              Save key
            </Button>
          </div>
        </form>
      </Card>
      {reKeyMutation.isSuccess && (
        <AlertBanner kind="success">
          Signed in as {reKeyMutation.data.player.name} (player id {reKeyMutation.data.player.playerId}).
        </AlertBanner>
      )}
      {reKeyMutation.isError && (
        <AlertBanner kind="error">{reKeyMutation.error instanceof ApiError ? reKeyMutation.error.message : 'Something went wrong.'}</AlertBanner>
      )}

      <div style={{ marginTop: 8 }}>
        <Button onClick={() => logoutMutation.mutate()} disabled={logoutMutation.isPending}>
          Log out
        </Button>
      </div>

      <hr />
      <SectionHeading>Privacy, Data &amp; Source</SectionHeading>
      <p>
        This app is fully open source —{' '}
        <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer">
          read the code on GitHub
        </a>
        .
      </p>
      <details>
        <summary>What's stored, and how to remove it</summary>
        <ul>
          <li>
            <strong>Your Torn player ID, name, and faction</strong> — used to scope every query to your account only.
          </li>
          <li>
            <strong>Synced snapshots and log entries</strong> — whatever you've pulled in via Sync, stored in a shared Postgres database, isolated
            per Torn player ID. No other player can see your data.
          </li>
          <li>
            <strong>Checklist tasks and category rules</strong> — your own personal setup.
          </li>
          <li>
            <strong>Premium/license status</strong> — whether you're on a trial, paid, or lifetime grant.
          </li>
        </ul>
        <p>
          To remove your synced data, use <strong>Clear DB</strong> on the Sync page — it
          permanently deletes your snapshots, log entries, and category rules. It does not
          currently remove your player record or Premium/license history; if you'd like your
          account fully deleted, contact the developer directly.
        </p>
        <p>
          This is an independent hobby project, not affiliated with or endorsed by Torn. It's
          provided as-is, with no warranty — use your own judgment, same as with any third-party
          tool that reads your Torn API data.
        </p>
      </details>

      <hr />
      <SectionHeading>Feedback &amp; Suggestions</SectionHeading>
      <p>
        Found a bug, or have an idea for a feature? Send a Torn message to{' '}
        <a href={DEV_PROFILE_URL} target="_blank" rel="noreferrer">
          {DEV_PROFILE_LABEL}
        </a>{' '}
        — all feedback and suggestions are welcome.
      </p>

      <hr />
      <SectionHeading>War Mode</SectionHeading>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, textTransform: 'none' }}>
        <input
          type="checkbox"
          style={{ width: 'auto' }}
          checked={warModeQuery.data?.active ?? false}
          onChange={(e) => warModeMutation.mutate(e.target.checked)}
        />
        War Mode active
      </label>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Turn this on during a ranked war. It drives auto-categorization of log entries as 'Ranked
        War' during sync, and controls which 'On War Days' checklist tasks are shown/reset.
      </p>

      <hr />
      <SectionHeading>Premium / License</SectionHeading>
      {premium.isPremium ? (
        premium.isLifetime ? (
          <AlertBanner kind="success">Premium active via {SOURCE_LABELS[premium.source] ?? premium.source} — forever.</AlertBanner>
        ) : (
          <AlertBanner kind={premium.isExpiringSoon ? 'warning' : 'success'}>
            Premium active via {SOURCE_LABELS[premium.source] ?? premium.source}
            {premium.premiumUntil && `, until ${formatTimestamp(premium.premiumUntil)}`}.
            {premium.isExpiringSoon && premium.daysUntilExpiry !== null && (
              <>
                {' '}
                Expires in <strong>{formatDays(premium.daysUntilExpiry)} day(s)</strong> — extend it below before it runs out.
              </>
            )}
          </AlertBanner>
        )
      ) : (
        <AlertBanner kind="info">Free tier.</AlertBanner>
      )}

      <p>
        Send <strong>1 Xanax</strong> to{' '}
        <a href={DEV_PROFILE_URL} target="_blank" rel="noreferrer">
          {DEV_PROFILE_LABEL}
        </a>{' '}
        for 4 weeks of Premium.
      </p>

      {!licensingQuery.data?.trialUsed && !premium.isPremium && (
        <Button onClick={() => trialMutation.mutate()} disabled={trialMutation.isPending}>
          Start my 7-day free trial
        </Button>
      )}
      {trialMutation.data && (
        <AlertBanner kind={trialMutation.data.started ? 'success' : 'error'}>
          {trialMutation.data.started
            ? `Trial started! Premium until ${formatTimestamp(trialMutation.data.premiumUntil!)}.`
            : trialMutation.data.reason}
        </AlertBanner>
      )}

      <h4 style={{ marginTop: 20 }}>Pay for Premium</h4>
      <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
          <input type="radio" style={{ width: 'auto' }} checked={payMode === 'individual'} onChange={() => setPayMode('individual')} />
          Just myself
        </label>
        {player.factionId && (
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
            <input type="radio" style={{ width: 'auto' }} checked={payMode === 'faction'} onChange={() => setPayMode('faction')} />
            My whole faction (bulk)
          </label>
        )}
      </div>

      {payMode === 'faction' ? (
        factionPreviewQuery.data ? (
          <p>
            Your faction has <strong>{factionPreviewQuery.data.memberCount}</strong> members (
            {factionPreviewQuery.data.discountPct > 0 ? `${(factionPreviewQuery.data.discountPct * 100).toFixed(0)}%` : 'no'} bulk discount) — send{' '}
            <strong>{factionPreviewQuery.data.required} Xanax</strong> total to cover everyone for 4 weeks
            {factionPreviewQuery.data.lifetimeCoveredCount > 0 &&
              ` (${factionPreviewQuery.data.lifetimeCoveredCount} member(s) already have lifetime Premium and aren't counted)`}
            .
          </p>
        ) : (
          <AlertBanner kind="warning">Could not read your faction's member list right now — try again shortly.</AlertBanner>
        )
      ) : (
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>1 Xanax covers 4 weeks of Premium for your account only.</p>
      )}

      <Button
        onClick={() => (payMode === 'faction' ? scanGroupPaymentMutation.mutate() : scanPaymentMutation.mutate())}
        disabled={scanPaymentMutation.isPending || scanGroupPaymentMutation.isPending}
      >
        Check my payment now
      </Button>

      {scanPaymentMutation.data && (
        <AlertBanner kind="info">
          {scanPaymentMutation.data.creditedCount > 0
            ? `Credited ${scanPaymentMutation.data.weeksAdded} week(s) from ${scanPaymentMutation.data.creditedCount} payment(s).`
            : 'No new qualifying payment found in the last 7 days.'}
        </AlertBanner>
      )}
      {scanGroupPaymentMutation.data && <AlertBanner kind="info">{scanGroupPaymentMutation.data.message}</AlertBanner>}

      {player.isAdmin && (
        <>
          <hr />
          <SectionHeading>Admin: Lifetime Premium Grants</SectionHeading>
          <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Only visible to the developer account.</p>

          <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
              <input type="radio" style={{ width: 'auto' }} checked={grantScope === 'individual'} onChange={() => setGrantScope('individual')} />
              Individual player
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, textTransform: 'none' }}>
              <input type="radio" style={{ width: 'auto' }} checked={grantScope === 'faction'} onChange={() => setGrantScope('faction')} />
              Faction
            </label>
          </div>
          <label htmlFor="grant-id">{grantScope === 'individual' ? 'Torn player ID' : 'Faction ID'}</label>
          <input id="grant-id" type="number" min={1} value={grantKey} onChange={(e) => setGrantKey(e.target.value)} style={{ maxWidth: 200 }} />
          <div style={{ marginTop: 8 }}>
            <Button onClick={() => createGrantMutation.mutate()} disabled={!grantKey || createGrantMutation.isPending}>
              Grant lifetime Premium
            </Button>
          </div>

          {grantsQuery.data && grantsQuery.data.grants.length > 0 ? (
            <div style={{ marginTop: 12 }}>
              <p>Current lifetime grants:</p>
              {grantsQuery.data.grants.map((grant) => (
                <div key={`${grant.scope}-${grant.key}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
                  <span>
                    <strong>{grant.scope}</strong> — {grant.key}
                  </span>
                  <Button onClick={() => revokeGrantMutation.mutate({ scope: grant.scope, key: grant.key })}>Revoke</Button>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>No lifetime grants yet.</p>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 3: Manually verify in the browser**

```bash
cd frontend && npm run dev
```
Log in, go to Settings. Confirm: the masked key line shows `****mock`; War Mode toggle flips and
persists across a page reload (mock state is in-memory, so only within the same tab session);
Premium section shows "Premium active via your payment" (mock's default `source: 'individual'`);
switching pay mode to "My whole faction (bulk)" shows the faction preview text; "Check my payment
now" shows the mock's response banner; since the mock player `isAdmin: true`, the Admin panel
renders with the seeded lifetime grant and working Grant/Revoke buttons.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/Settings.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add Settings page"
```

---

### Task 13: Categories page

**Files:**
- Modify: `frontend/src/pages/Categories.tsx` (replaces Task 7's placeholder)

**Interfaces:**
- Consumes: `useAuth()` (Task 7); `getCategories`, `createCategory`, `deleteCategory`,
  `getTitleSummary`, `reassignCategory` (Task 4 `categories.ts`); `ApiError` (Task 3); UI
  primitives (Task 2).

- [ ] **Step 1: Write `frontend/src/pages/Categories.tsx`**

```tsx
import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getCategories, createCategory, deleteCategory, getTitleSummary, reassignCategory } from '../api/categories';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

const RESERVED_NAMES = new Set(['Uncategorized', 'Ignored']);

export default function CategoriesPage() {
  const { premium } = useAuth();

  if (!premium?.isPremium) {
    return (
      <div className="page">
        <SectionHeading premium>Categories</SectionHeading>
        <AlertBanner kind="warning">
          Categories is a Premium feature. Start your free trial, pay with Xanax, or check faction
          options on the Settings page.
        </AlertBanner>
      </div>
    );
  }

  return <CategoriesContent />;
}

function CategoriesContent() {
  const queryClient = useQueryClient();
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories });

  const [newCategoryName, setNewCategoryName] = useState('');
  const [addError, setAddError] = useState<string | null>(null);
  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      setNewCategoryName('');
      setAddError(null);
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
    onError: (err) => setAddError(err instanceof ApiError ? err.message : 'Something went wrong.'),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  });

  function handleAddCategory(e: FormEvent) {
    e.preventDefault();
    const name = newCategoryName.trim();
    if (!name) {
      setAddError('Enter a name.');
      return;
    }
    if (RESERVED_NAMES.has(name)) {
      setAddError(`'${name}' is reserved and can't be used as a custom category.`);
      return;
    }
    createMutation.mutate(name);
  }

  return (
    <div className="page">
      <SectionHeading>Categories</SectionHeading>

      <SectionHeading>Manage Categories</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Categories used across Sync, Dashboard, and auto-categorization. A category can only be
        removed once no log entries use it.
      </p>

      <Card>
        <form onSubmit={handleAddCategory} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="new-category">New category name</label>
            <input id="new-category" value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} />
          </div>
          <Button type="submit" disabled={createMutation.isPending}>
            Add category
          </Button>
        </form>
      </Card>
      {addError && <AlertBanner kind="error">{addError}</AlertBanner>}

      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Entries</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(categoriesQuery.data?.categories ?? []).map((cat) => (
            <tr key={cat.name}>
              <td>{cat.name}</td>
              <td>
                {cat.entryCount} entr{cat.entryCount === 1 ? 'y' : 'ies'}
              </td>
              <td>
                <Button
                  variant="danger"
                  disabled={cat.entryCount > 0}
                  title={cat.entryCount > 0 ? 'Remove or recategorize its entries first' : undefined}
                  onClick={() => deleteMutation.mutate(cat.name)}
                >
                  Delete
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <hr />
      <ReviewAndRecategorize categories={(categoriesQuery.data?.categories ?? []).map((c) => c.name)} />
    </div>
  );
}

function ReviewAndRecategorize({ categories }: { categories: string[] }) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('All');
  const summaryQuery = useQuery({
    queryKey: ['categories', 'titleSummary', filter],
    queryFn: () => getTitleSummary(filter === 'All' ? undefined : filter),
  });

  const [edits, setEdits] = useState<Record<string, string>>({});
  useEffect(() => setEdits({}), [summaryQuery.data]);

  const reassignMutation = useMutation({ mutationFn: reassignCategory });

  const filterOptions = ['All', ...categories, 'Uncategorized', 'Ignored'];
  const categoryOptions = [...categories, 'Uncategorized', 'Ignored'];
  const rows = summaryQuery.data?.rows ?? [];
  const changedCount = rows.filter((row) => edits[row.title] && edits[row.title] !== row.category).length;

  async function handleApply() {
    const changedRows = rows.filter((row) => edits[row.title] && edits[row.title] !== row.category);
    for (const row of changedRows) {
      await reassignMutation.mutateAsync({ title: row.title, fromCategory: row.category, toCategory: edits[row.title] });
    }
    setEdits({});
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  }

  return (
    <>
      <SectionHeading>Review &amp; Recategorize</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Every log title seen so far, grouped by its current category. Edit the Category column and
        click Apply to reassign all matching entries — the choice is also remembered for future
        syncs.
      </p>

      <label htmlFor="title-filter">Filter by category</label>
      <select id="title-filter" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 240 }}>
        {filterOptions.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      {rows.length === 0 ? (
        <AlertBanner kind="info">No log entries yet.</AlertBanner>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Entries</th>
                <th>Category</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.title}>
                  <td>{row.title}</td>
                  <td>{row.entryCount}</td>
                  <td>
                    <select
                      value={edits[row.title] ?? row.category}
                      onChange={(e) => setEdits((prev) => ({ ...prev, [row.title]: e.target.value }))}
                    >
                      {categoryOptions.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 12 }}>
            <Button variant="primary" onClick={handleApply} disabled={changedCount === 0 || reassignMutation.isPending}>
              Apply changes
            </Button>
          </div>
          {reassignMutation.isSuccess && changedCount === 0 && <AlertBanner kind="success">Changes applied.</AlertBanner>}
        </>
      )}
    </>
  );
}
```

- [ ] **Step 2: Verify typecheck and build**

Run: `cd frontend && npm run typecheck && npm run build`
Expected: both exit 0.

- [ ] **Step 3: Manually verify in the browser**

```bash
cd frontend && npm run dev
```
Log in, go to Categories (mock player is Premium, so the page renders directly — temporarily set
`mockPremium.isPremium = false` in `src/mocks/data.ts` and reload to confirm the upsell banner
shows instead, then revert). Confirm: the category list shows entry counts, adding a duplicate or
reserved name shows the inline error, deleting a category with 0 entries works and one with
entries stays disabled; the Review & Recategorize table lists the mock's log titles, changing a
row's Category dropdown enables "Apply changes", and clicking it calls `reassignCategory` per
changed row and refreshes the category counts above.

- [ ] **Step 4: Commit**

```bash
cd frontend
git add src/pages/Categories.tsx
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add Categories page"
```

---

### Task 14: Polish, full golden-path verification, README

**Files:**
- Create: `frontend/README.md`
- Modify: none expected, but fix anything the checks below surface (e.g. a missed `credentials:
  'include'`, a stray `border-radius`, an unused import ESLint flags)

**Interfaces:** none new — this task only verifies and documents everything Tasks 1-13 produced.

- [ ] **Step 1: Run the full automated check suite**

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
npx vitest run
```
Expected: all four exit 0. If `lint` flags anything (unused vars, missing deps in a `useEffect`
array, etc.), fix it in the relevant page/component file before continuing.

- [ ] **Step 2: Grep for constraint violations**

```bash
cd frontend
grep -rn "fetch(" src --include="*.ts" --include="*.tsx" | grep -v "src/api/client.ts" | grep -v "src/mocks/"
grep -rn "border-radius" src/styles/theme.css | grep -v "border-radius: 0"
```
Expected: the first command returns nothing (every real `fetch` call lives only in
`client.ts`/mock handlers); the second returns nothing (no non-zero `border-radius` anywhere). If
either finds something, fix it before continuing — this is the exact class of regression the
Global Constraints section calls out as easy to silently introduce.

- [ ] **Step 3: Full golden-path browser walkthrough against the mocks**

```bash
cd frontend
npm run dev
```
(`.env` already has `VITE_USE_MOCKS=true` from Task 7.) Walk the entire path in one continuous
session, in order, confirming each step before moving to the next:

1. Login page loads after the cold-start panel; log in with any non-`invalid` key.
2. Home: signed-in banner, last-synced line, all nav cards, footer links present.
3. Sync: click "Sync now" (success banner with counts), click "Get all Data" (progress banner
   updates through completion), edit and save the Period Note, Save/Ignore an uncategorized entry
   (it disappears from the list), expand Ignored and Restore an entry, check the Danger Zone
   checkbox and click Clear DB (Dashboard should then show "need at least one snapshot").
4. Click "Sync now" again to repopulate data, then go to Dashboard: cycle through all five
   time-range presets including Custom, confirm both KPI cards/charts/tables update, click "Export
   CSV".
5. Checklist: add a task with each repeat type (confirm the "Every X days" field only appears for
   `every_x_days`), mark one done (moves to Completed), un-check it from Completed, edit a task,
   delete a task.
6. Settings: re-save the API key, toggle War Mode (then check the Checklist page shows/hides the
   `war_day` task accordingly), start the free trial (button disappears afterward), switch pay
   mode to faction and back, click "Check my payment now", grant and then revoke a lifetime grant
   in the Admin panel.
7. Categories: add a category, attempt to delete one that's in use (stays disabled), change a row
   in Review & Recategorize and click Apply, confirm the category counts above update.
8. Click Log out — confirm the Login page reappears.

Fix any issue found in the relevant page file, then re-run the specific step (no need to redo the
whole walkthrough) before continuing.

- [ ] **Step 4: Write `frontend/README.md`**

```markdown
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
```

- [ ] **Step 5: Final full verification run and commit**

```bash
cd frontend
npm run typecheck && npm run lint && npm run build && npx vitest run
git add README.md
git status
```
Confirm `git status` shows only the intended files across the whole plan (no stray `.env`,
`node_modules`, or `dist` — those are gitignored per Task 1). Then:
```bash
GIT_AUTHOR_NAME="M3mphistus" GIT_AUTHOR_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_COMMITTER_NAME="M3mphistus" GIT_COMMITTER_EMAIL="213164151+M3mphistus@users.noreply.github.com" \
GIT_AUTHOR_DATE="$(date +%s) -0700" GIT_COMMITTER_DATE="$(date +%s) -0700" \
git commit -m "Add frontend README and complete golden-path verification"
```

If Step 1-3 required any fixes to earlier pages/components, stage and commit those separately
first (with the same git identity), scoped to whichever file changed, before this final commit —
don't bundle unrelated fixes into the README commit.

---

## Self-Review Notes

**Spec coverage**: every page/feature in `FRONTEND_PROMPT.md`'s "Pages / features to build"
section maps to a task — Login/Auth (Task 7), Home (Task 8), Dashboard (Task 9), Sync (Task 10),
Checklist (Task 11), Settings (Task 12), Categories (Task 13). Every endpoint in `API_CONTRACT.md`
has a corresponding function in Task 4's domain modules and a corresponding MSW handler in Task
6. The theme's motifs (square corners, hairline borders, diamond bullets, KPI corner brackets,
uppercase buttons, left-gold-border banners, Premium badge) are all in Task 1's `theme.css`. Cold-
start UX is Task 7's `ColdStartLoader`. The Render deployment specifics and Safari cookie caveat
are documented in Task 14's README.

**Known deliberate simplification** (flagged in Global Constraints, not a gap): the developer's
Torn profile ID/name used in "send a Torn message to ___" copy is hardcoded in `constants.ts` from
`backend/.env.example`'s values, since no API endpoint exposes it. Correcting the name (if it's
wrong) is a one-line change, not a re-plan.

**Type consistency check**: `AuthState` (Task 7) fields (`player`, `premium`, `isLoading`,
`isAuthenticated`, `isUnauthenticated`, `error`, `refetch`) are used identically by every consumer
(`App.tsx`, `AppShell`, `Home`, `Sync`, `Checklist`, `Settings`, `Categories`) — none destructure a
field not defined there. `ChecklistTaskInput` (Task 4) is used with matching field names
(`title`, `description`, `repeatType`, `repeatIntervalDays`) in both Task 4's `createTask`/
`updateTask` and Task 11's form state. Query key prefixes (`['auth', ...]`, `['snapshots', ...]`,
`['dashboard', ...]`, `['log-entries', ...]`, `['categories', ...]`, `['checklist']`,
`['warMode']`, `['licensing', ...]`, `['admin', ...]`, `['syncJob', ...]`) are consistent between
the query that fetches data and the `invalidateQueries` calls that follow a mutation on the same
resource, in every page task from Task 8 onward.

