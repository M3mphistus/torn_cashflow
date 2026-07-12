# API Contract — Torn Cashflow (React + FastAPI rewrite)

This is the single source of truth for the REST contract between the backend (FastAPI) and
frontend (React). **Both `BACKEND_PROMPT.md` and `FRONTEND_PROMPT.md` reference this file —
if you are implementing either side, follow this exactly rather than improvising field names
or shapes.** The two sides are being built in separate, isolated AI sessions with no way to
ask each other questions, so drift here is the single biggest risk to the whole rewrite.

## Global conventions

- **Base path**: all endpoints below are prefixed with `/api` (health check is the only
  exception: `GET /health` with no prefix).
- **JSON casing**: every JSON key at the HTTP boundary is `camelCase`. The backend's internal
  Python/DB layer stays `snake_case`; convert at the API boundary (e.g. Pydantic models with
  `alias_generator` set to camelCase, or FastAPI response models that just declare camelCase
  field names).
- **Timestamps**: always unix seconds, as a JSON integer (`number`), never an ISO string, never
  milliseconds. This matches the existing Postgres schema (`BIGINT` columns) exactly.
- **`amount` is `number | null`, never coerced to `0`.** `null` means "Torn didn't report an
  amount for this log entry" and is a meaningfully different state from a `0` amount — the
  free-tier auto-categorization logic routes null-amount + uncategorized entries into the
  `Ignored` category automatically. Do not lose this distinction anywhere in the pipeline.
- **Auth cookie**: name `session_token`. Set by `POST /api/auth/login`, `httpOnly`, `Secure`,
  `SameSite=None`, `Path=/`, long-lived (~400 days, matching browsers' own cookie lifetime cap —
  there's no reason to expire it sooner given this is the "stay signed in" mechanism the old
  Streamlit app already had). Every authenticated endpoint reads this cookie server-side; the
  frontend never sees or stores the JWT directly except via the browser's own cookie jar.
- **Frontend requirement**: every `fetch()` call to the backend must set
  `credentials: 'include'` explicitly — this is required for the cross-site cookie
  (frontend and backend are on different `*.onrender.com` subdomains) and is easy to silently
  omit with the native `fetch` API. A shared API client wrapper that always sets this is
  strongly recommended over calling `fetch` ad hoc.
- **Auth failure**: any endpoint requiring auth returns `401` with the standard error shape
  below when the `session_token` cookie is missing/invalid/expired. The frontend should treat a
  `401` from `GET /api/auth/me` as "not logged in" (show the login form), not as an error to
  surface to the user.
- **Error response shape** (used for all non-2xx responses):
  ```json
  {
    "error": {
      "message": "Human-readable message safe to show the user",
      "code": "short_snake_case_machine_code",
      "tornErrorCode": 2
    }
  }
  ```
  `tornErrorCode` is present (int) only when the error originated from a Torn API error
  response (see `torn_api.py`'s `ERROR_MESSAGES` for the code list); otherwise `null`/omitted.
- **Premium-gated endpoints** return `403` with `code: "premium_required"` when the caller is
  authenticated but not Premium.

---

## Auth

### `POST /api/auth/login`
Request:
```json
{ "apiKey": "abc123..." }
```
Validates the key against Torn's `/user/?selections=profile` endpoint (see
`torn_api.get_basic_profile`), upserts the `players` row, encrypts and stores the key
server-side, issues the session cookie.

Response `200`:
```json
{ "player": PlayerDTO, "premium": PremiumStatusDTO }
```
Errors: `400` empty/malformed key; `401` with `tornErrorCode` when Torn rejects the key
(most commonly code `2`, "Incorrect API key"); `502` on `TornNetworkError` (Torn unreachable/timeout).

### `POST /api/auth/logout`
Clears the session cookie server-side (and should clear/leave the stored `players.api_key` —
your call, see `BACKEND_PROMPT.md`). Response `204`.

### `GET /api/auth/me`
Response `200`: `{ "player": PlayerDTO, "premium": PremiumStatusDTO }` if the session cookie is
valid. `401` otherwise (this is the normal "am I logged in" bootstrap call the frontend makes
on every page load — a 401 here is expected/routine, not exceptional).

**`PlayerDTO`**:
```json
{
  "playerId": 123456,
  "name": "SomePlayer",
  "factionId": 7890,
  "maskedApiKey": "****abcd"
}
```
The raw API key is **never** returned in any response body, ever — only the masked form
(reuse the existing `mask_key()` logic: all but the last 4 characters replaced with `*`).

**`PremiumStatusDTO`**:
```json
{
  "isPremium": true,
  "premiumUntil": 1799999999,
  "isLifetime": false,
  "source": "individual",
  "isExpiringSoon": false,
  "daysUntilExpiry": 12.4
}
```
`source` is one of: `"none" | "trial" | "individual" | "faction" | "lifetimeIndividual" | "lifetimeFaction"`.
`premiumUntil`/`daysUntilExpiry` are `null` when `isPremium` is `false`, and `daysUntilExpiry`
is also `null` when `isLifetime` is `true` (nothing meaningful to warn about).

---

## Sync

### `POST /api/sync/incremental`
Pulls bars/money/personalstats + log since the player's last sync (or the last 7 days if never
synced), stores a new snapshot + new log entries, auto-categorizes them, runs the post-sync
payment check (see Licensing).

Response `200`:
```json
{
  "snapshot": SnapshotDTO,
  "logEntriesStored": 14,
  "paymentMessage": "Credited 4 week(s) of Premium from 1 Xanax payment(s)."
}
```
`paymentMessage` is `null` when nothing new was credited. Errors: `401`/`502` per Torn error
handling above.

### `POST /api/sync/full-history`
**Premium-gated** (`403 premium_required` if not Premium). Starts an async background job —
see `BACKEND_PROMPT.md` for why this cannot be synchronous on Render's free tier. Immediately
returns without waiting for completion.

Response `202`:
```json
{ "jobId": 42, "status": "running" }
```

### `GET /api/sync/full-history/{jobId}`
Polling endpoint. Response `200`:
```json
{
  "jobId": 42,
  "status": "running",
  "pagesFetched": 12,
  "entriesFetched": 1180,
  "oldestTimestamp": 1700000000,
  "error": null,
  "result": null
}
```
`status` is one of `"running" | "completed" | "failed"`. When `"completed"`, `result` is:
```json
{ "newEntriesStored": 1180, "alreadyStored": 40 }
```
When `"failed"`, `error` holds a human-readable message and `result` stays `null`. The frontend
should poll every ~2-3 seconds and treat a job with no progress update for a long stretch
(e.g. 60s) as stalled — offer retry rather than polling forever.

---

## Snapshots & Dashboard

### `GET /api/snapshots?startTs=&endTs=`
Both query params optional (unix seconds). Response `200`: `{ "snapshots": SnapshotDTO[] }`,
ordered ascending by `syncedAt`.

### `GET /api/snapshots/latest`
Response `200`: `{ "snapshot": SnapshotDTO | null }`.

### `PATCH /api/snapshots/{id}/note`
Request: `{ "note": "text" }`. Response `200`: `{ "snapshot": SnapshotDTO }`.

**`SnapshotDTO`** (camelCase mirror of the `api_snapshots` table — see `BACKEND_PROMPT.md` for
the full column list):
```json
{
  "id": 501,
  "syncedAt": 1730000000,
  "moneyOnhand": 500000,
  "moneyPoints": 12000,
  "vaultAmount": 2000000,
  "bankAmount": 100000,
  "energyCurrent": 90, "energyMaximum": 150,
  "nerveCurrent": 20, "nerveMaximum": 50,
  "happyCurrent": 4000, "happyMaximum": 5000,
  "networth": 15000000,
  "nwPending": 0, "nwWallet": 500000, "nwBank": 100000, "nwPoints": 1200000,
  "nwCayman": 0, "nwVault": 2000000, "nwPiggybank": 0, "nwItems": 3000000,
  "nwDisplaycase": 0, "nwBazaar": 0, "nwItemmarket": 0, "nwProperties": 5000000,
  "nwStockmarket": 0, "nwAuctionhouse": 0, "nwCompany": 0, "nwBookie": 0,
  "nwEnlistedcars": 0, "nwLoan": 0, "nwUnpaidfees": 0,
  "refillsTotal": 40, "nerverefillsTotal": 5, "energydrinkusedTotal": 12, "xantakenTotal": 8,
  "warModeActive": false,
  "note": "War week 1"
}
```

### `GET /api/dashboard?startTs=&endTs=`
The one aggregate endpoint for the whole Dashboard page — computed server-side (reusing
`calculations.py` logic) so the frontend never has to reimplement pandas-equivalent math in
JS. Both params required (frontend resolves the selected time-range preset to concrete
timestamps before calling).

Response `200`:
```json
{
  "cashflowTotal": 2500000,
  "cashflowPerDay": 178571.4,
  "categoryBreakdown": [
    { "category": "Ranked War", "amount": 1200000 },
    { "category": "Job", "amount": -300000 }
  ],
  "networthBreakdown": [
    { "component": "Networth Total", "amount": 15000000 },
    { "component": "Trade", "amount": null }
  ],
  "dailyCashflow": [
    { "date": "2026-06-01", "cashflowDelta": 120000 }
  ],
  "dailyNetworth": [
    { "date": "2026-06-01", "networth": 14500000 }
  ],
  "snapshots": [ SnapshotDTO ]
}
```
`snapshots` here is the same list `GET /api/snapshots` would return for that range — included
so the Dashboard's raw-snapshot table and CSV export don't need a second round-trip.
`networthBreakdown` always has all 20 rows (19 named components + "Trade", which is always
`null` — Torn's API doesn't expose it, see `calculations.NETWORTH_BREAKDOWN_FIELDS`), in the
same fixed order as that list.

---

## Log entries

### `GET /api/log-entries?startTs=&endTs=&category=`
All params optional. Response `200`: `{ "entries": LogEntryDTO[] }`.

### `GET /api/log-entries/uncategorized?limit=25`
Response `200`: `{ "entries": LogEntryDTO[], "totalCount": 143 }` — `entries` is capped at
`limit` (default 25, matches old `ENTRY_LIST_DISPLAY_LIMIT`), `totalCount` is the true total so
the frontend can show "showing 25 of 143".

### `GET /api/log-entries/ignored?limit=25`
Same shape as above, for entries with `appCategory == "Ignored"`.

### `PATCH /api/log-entries/{id}`
Request: `{ "appCategory": "Job", "userNote": "optional text" }`. Updates this entry, **and**
(mirroring the old Streamlit behavior) upserts a category rule for this entry's title and
bulk-applies the new category to every other still-`Uncategorized` entry with the same title.

Response `200`: `{ "entry": LogEntryDTO, "bulkUpdatedCount": 3 }`.

### `POST /api/log-entries/{id}/ignore`
Request: `{ "userNote": "optional text" }`. Same bulk-by-title behavior as above but sets
category to `"Ignored"`. Response `200`: `{ "entry": LogEntryDTO, "bulkUpdatedCount": 3 }`.

### `POST /api/log-entries/{id}/restore`
Sets this single entry's `appCategory` back to `"Uncategorized"` (no bulk side-effect — mirrors
the old "Restore" button on ignored entries). Response `200`: `{ "entry": LogEntryDTO }`.

### `POST /api/log-entries/recategorize-period`
Request: `{ "startTs": 1700000000, "endTs": 1700600000, "appCategory": "Ranked War" }`.
Response `200`: `{ "updatedCount": 40 }`.

**`LogEntryDTO`**:
```json
{
  "id": 9001,
  "tornLogId": "1234567890",
  "timestamp": 1730000500,
  "category": "Item sending",
  "title": "Item send",
  "rawText": "You sent 4x Xanax to SomePlayer",
  "amount": null,
  "appCategory": "Uncategorized",
  "userNote": null
}
```

---

## Categories

### `GET /api/categories`
Response `200`: `{ "categories": [ { "name": "Flying", "entryCount": 12 } ] }`.

### `POST /api/categories`
Request: `{ "name": "Custom Category" }`. `201` on success with `{ "name": "Custom Category" }`.
`409` if the name already exists or is reserved (`"Uncategorized"` / `"Ignored"`).

### `DELETE /api/categories/{name}`
`204` on success. `409` (with a clear message) if any log entry still uses this category — the
old UI disabled the delete button in this case; the backend is the enforcement point here.

### `GET /api/categories/title-summary?filterCategory=`
`filterCategory` optional. Response `200`:
```json
{ "rows": [ { "title": "Attacked player X", "category": "Ranked War", "entryCount": 6 } ] }
```

### `POST /api/categories/reassign`
Request: `{ "title": "Attacked player X", "fromCategory": "Uncategorized", "toCategory": "Ranked War" }`.
Bulk-reassigns every entry matching `title` + `fromCategory`, and upserts the category rule.
Response `200`: `{ "updatedCount": 6 }`.

---

## Checklist

### `GET /api/checklist`
Applies the Premium auto-reset pass server-side before returning (see `calculations.task_needs_reset`
— on Premium, any task whose cycle has elapsed gets reset as a side effect of this call, same as
the old page-load behavior). Response `200`: `{ "tasks": ChecklistTaskDTO[] }`.

### `POST /api/checklist`
Request: `{ "title": "...", "description": "...", "repeatType": "daily", "repeatIntervalDays": null }`.
`repeatType` is one of `"daily" | "weekly" | "every_x_days" | "once" | "war_day"`.
`repeatIntervalDays` is required (int ≥ 1) only when `repeatType == "every_x_days"`, else `null`.
Response `201`: `{ "task": ChecklistTaskDTO }`.

### `PATCH /api/checklist/{id}`
Same body shape as create. Response `200`: `{ "task": ChecklistTaskDTO }`.

### `DELETE /api/checklist/{id}`
`204`.

### `POST /api/checklist/{id}/done`
Request: `{ "done": true }`. Sets `isDoneCurrentCycle` and stamps/clears `lastCompletedAt`
accordingly (mirrors old `set_task_done`: `lastCompletedAt = now` when marking done, left
unchanged when marking not-done). Response `200`: `{ "task": ChecklistTaskDTO }`.

**`ChecklistTaskDTO`**:
```json
{
  "id": 12,
  "title": "Use energy refill",
  "description": "Spend the daily energy refill before it resets.",
  "repeatType": "daily",
  "repeatIntervalDays": null,
  "createdAt": 1700000000,
  "lastCompletedAt": 1730000000,
  "isDoneCurrentCycle": true
}
```

---

## Settings / War Mode

### `GET /api/settings/war-mode`
Response `200`: `{ "active": true, "startedAt": 1730000000 }` (`startedAt` is `null` if never
turned on).

### `PUT /api/settings/war-mode`
Request: `{ "active": true }`. When turning on (`false -> true`), stamps `startedAt = now`;
turning off leaves the stored `startedAt` as-is (matches old behavior — it's read again next
time War Mode turns on... actually re-check: old code always re-stamps `war_mode_started_at`
every time it flips to `true`). Response `200`: `{ "active": true, "startedAt": 1730000000 }`.

---

## Licensing

### `GET /api/licensing/status`
Response `200`: `PremiumStatusDTO` fields plus `{ "trialUsed": false }`.

### `POST /api/licensing/trial`
No body. Response `200`:
```json
{ "started": true, "reason": null, "premiumUntil": 1730600000 }
```
or, if already used: `{ "started": false, "reason": "Trial already used.", "premiumUntil": null }`.

### `POST /api/licensing/scan-payment`
Request: `{ "lookbackDays": 7 }` (optional, defaults to 7). Response `200`:
```json
{ "creditedCount": 1, "weeksAdded": 4, "newPremiumUntil": 1730600000, "alreadyCreditedCount": 0 }
```

### `GET /api/licensing/faction-preview`
Response `200` if the player is in a faction:
```json
{ "memberCount": 34, "lifetimeCoveredCount": 2, "payableMembers": 32, "discountPct": 0.1, "required": 29 }
```
`204` (no body) if the player has no faction.

### `POST /api/licensing/scan-group-payment`
Request: `{ "lookbackDays": 7 }` (optional). Response `200`:
```json
{ "activated": true, "message": "Faction license activated for 34 members (29 Xanax sent, 29 required).", "required": 29, "sent": 29 }
```

---

## Admin

All three require the caller to be the hardcoded dev/admin player (see `licensing.is_admin`) —
`403` for everyone else, and the frontend should not even render the admin panel for non-admins
(check `GET /api/auth/me`'s player against a client-visible "am I admin" flag — add
`"isAdmin": boolean` to `PlayerDTO` returned by `/auth/login` and `/auth/me` for this purpose).

### `GET /api/admin/lifetime-grants`
Response `200`: `{ "grants": [ { "scope": "individual", "key": 123456, "activatedAt": 1700000000 } ] }`.
`scope` is `"individual" | "faction"`; `key` is the player ID or group/faction ID depending on scope.

### `POST /api/admin/lifetime-grants`
Request: `{ "scope": "individual", "key": 123456 }`. `201`.

### `DELETE /api/admin/lifetime-grants`
Request body: `{ "scope": "individual", "key": 123456 }`. `204`.

---

## Data management

### `DELETE /api/data`
Clears all synced snapshots/log entries/category rules for the current player (checklist tasks
and War Mode setting are untouched — matches old `clear_synced_data`). `204`. The frontend must
require an explicit confirmation step before calling this (old UI: a checkbox that enables the
button) — this is destructive and irreversible.

---

## Health

### `GET /health`
No auth, no DB, no Torn call — just `200 "ok"`. Used by Render's health check.
