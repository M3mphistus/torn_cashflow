import time

import streamlit as st
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

CACHE_TTL_SECONDS = 60  # short safety-net TTL; every write below clears its own caches
# immediately, so the acting session always sees its own change right away regardless of TTL.

SEED_TASKS = [
    {
        "title": "Use energy refill",
        "description": "Spend the daily energy refill before it resets.",
        "repeat_type": "daily",
        "repeat_interval_days": None,
    },
    {
        "title": "Check nerve/energy ticks via timer",
        "description": "Check regen timers so bars don't overflow unused.",
        "repeat_type": "daily",
        "repeat_interval_days": None,
    },
    {
        "title": "Stack energy before war",
        "description": "Save up energy ahead of the next ranked war.",
        "repeat_type": "war_day",
        "repeat_interval_days": None,
    },
    {
        "title": "Coordinate hit allocation with chain leader",
        "description": "Sync with the chain leader on hit assignment for the war.",
        "repeat_type": "war_day",
        "repeat_interval_days": None,
    },
    {
        "title": "Build trade partner for flowers",
        "description": "Find a reliable trade partner for the flowers business.",
        "repeat_type": "once",
        "repeat_interval_days": None,
    },
]

SEED_CATEGORIES = [
    "Flying",
    "Ranked War",
    "Crimes & OCs",
    "Gym & Happy Jumps",
    "Job",
    "Stock Market",
    "Transfer",
    "Gift",
    "Casino",
    "Other",
]

NETWORTH_BREAKDOWN_COLUMNS = [
    "nw_pending", "nw_wallet", "nw_bank", "nw_points", "nw_cayman", "nw_vault",
    "nw_piggybank", "nw_items", "nw_displaycase", "nw_bazaar", "nw_itemmarket",
    "nw_properties", "nw_stockmarket", "nw_auctionhouse", "nw_company", "nw_bookie",
    "nw_enlistedcars", "nw_loan", "nw_unpaidfees",
]


@st.cache_resource
def get_pool() -> ConnectionPool:
    return ConnectionPool(
        conninfo=st.secrets["DATABASE_URL"],
        min_size=1,
        max_size=5,
        # prepare_threshold=None disables server-side prepared statements, required when
        # connecting through Supabase/PgBouncer's transaction-mode pooler, which doesn't
        # keep a stable underlying connection across statements.
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None},
    )


def init_db() -> None:
    with get_pool().connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_snapshots (
                id BIGSERIAL PRIMARY KEY,
                torn_player_id BIGINT NOT NULL,
                synced_at BIGINT NOT NULL,
                money_onhand BIGINT,
                money_points BIGINT,
                vault_amount BIGINT,
                bank_amount BIGINT,
                energy_current INTEGER,
                energy_maximum INTEGER,
                nerve_current INTEGER,
                nerve_maximum INTEGER,
                happy_current INTEGER,
                happy_maximum INTEGER,
                networth BIGINT,
                nw_pending BIGINT,
                nw_wallet BIGINT,
                nw_bank BIGINT,
                nw_points BIGINT,
                nw_cayman BIGINT,
                nw_vault BIGINT,
                nw_piggybank BIGINT,
                nw_items BIGINT,
                nw_displaycase BIGINT,
                nw_bazaar BIGINT,
                nw_itemmarket BIGINT,
                nw_properties BIGINT,
                nw_stockmarket BIGINT,
                nw_auctionhouse BIGINT,
                nw_company BIGINT,
                nw_bookie BIGINT,
                nw_enlistedcars BIGINT,
                nw_loan BIGINT,
                nw_unpaidfees BIGINT,
                refills_total BIGINT,
                nerverefills_total BIGINT,
                energydrinkused_total BIGINT,
                xantaken_total BIGINT,
                war_mode_active BOOLEAN NOT NULL DEFAULT FALSE,
                note TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_snapshots_player_synced "
            "ON api_snapshots (torn_player_id, synced_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS log_entries (
                id BIGSERIAL PRIMARY KEY,
                torn_player_id BIGINT NOT NULL,
                snapshot_id BIGINT NOT NULL REFERENCES api_snapshots(id) ON DELETE CASCADE,
                torn_log_id TEXT,
                timestamp BIGINT NOT NULL,
                category TEXT,
                title TEXT,
                raw_text TEXT,
                amount DOUBLE PRECISION,
                app_category TEXT NOT NULL DEFAULT 'Uncategorized',
                user_note TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_entries_player_ts ON log_entries (torn_player_id, timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_entries_player_category "
            "ON log_entries (torn_player_id, app_category)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_log_entries_player_logid "
            "ON log_entries (torn_player_id, torn_log_id) WHERE torn_log_id IS NOT NULL"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checklist_tasks (
                id BIGSERIAL PRIMARY KEY,
                torn_player_id BIGINT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                repeat_type TEXT NOT NULL,
                repeat_interval_days INTEGER,
                created_at BIGINT NOT NULL,
                last_completed_at BIGINT,
                is_done_current_cycle BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_checklist_tasks_player ON checklist_tasks (torn_player_id, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                torn_player_id BIGINT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (torn_player_id, key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS category_rules (
                torn_player_id BIGINT NOT NULL,
                title TEXT NOT NULL,
                app_category TEXT NOT NULL,
                PRIMARY KEY (torn_player_id, title)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                torn_player_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                PRIMARY KEY (torn_player_id, name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                torn_player_id BIGINT PRIMARY KEY,
                name TEXT,
                faction_id BIGINT,
                trial_used_at BIGINT,
                last_seen_at BIGINT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS licenses (
                id BIGSERIAL PRIMARY KEY,
                scope TEXT NOT NULL CHECK (scope IN ('individual', 'faction')),
                torn_player_id BIGINT,
                group_id BIGINT,
                premium_until BIGINT NOT NULL,
                activated_at BIGINT NOT NULL,
                last_payment_torn_log_id TEXT,
                origin TEXT NOT NULL DEFAULT 'payment' CHECK (origin IN ('payment', 'trial', 'lifetime')),
                CONSTRAINT chk_license_key CHECK (
                    (scope = 'individual' AND torn_player_id IS NOT NULL AND group_id IS NULL)
                    OR (scope = 'faction' AND group_id IS NOT NULL AND torn_player_id IS NULL)
                )
            )
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_license_individual "
            "ON licenses (torn_player_id) WHERE scope = 'individual'"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_license_group "
            "ON licenses (scope, group_id) WHERE scope = 'faction'"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS credited_payments (
                id BIGSERIAL PRIMARY KEY,
                torn_log_id TEXT NOT NULL,
                payer_player_id BIGINT NOT NULL,
                credited_scope TEXT NOT NULL,
                credited_group_id BIGINT,
                weeks_granted INTEGER NOT NULL,
                credited_at BIGINT NOT NULL,
                UNIQUE (torn_log_id, payer_player_id)
            )
            """
        )
    _migrate_licenses_origin_check()


def _migrate_licenses_origin_check() -> None:
    """Widen the origin CHECK constraint to allow 'lifetime' on tables created
    before that value existed. CREATE TABLE IF NOT EXISTS won't touch an
    already-created table's constraints, so this runs unconditionally each
    startup — cheap no-op once the constraint is already up to date."""
    with get_pool().connection() as conn:
        conn.execute("ALTER TABLE licenses DROP CONSTRAINT IF EXISTS licenses_origin_check")
        conn.execute(
            "ALTER TABLE licenses ADD CONSTRAINT licenses_origin_check "
            "CHECK (origin IN ('payment', 'trial', 'lifetime'))"
        )


def _invalidate_log_caches() -> None:
    """Clear every cached read derived from api_snapshots/log_entries. Called by any
    write that touches those tables, so the acting session sees its change immediately."""
    get_snapshots.clear()
    get_latest_snapshot.clear()
    get_existing_torn_log_ids.clear()
    get_log_entries.clear()
    get_log_entry_timestamp_range.clear()
    get_entries_by_category.clear()
    get_category_counts.clear()
    get_title_category_summary.clear()


def _invalidate_category_caches() -> None:
    list_categories.clear()
    get_all_category_rules.clear()


def _invalidate_checklist_cache() -> None:
    list_checklist_tasks.clear()


def _invalidate_license_caches() -> None:
    get_license.clear()
    list_lifetime_grants.clear()
    count_lifetime_individual.clear()


def upsert_player(torn_player_id: int, name: str | None, faction_id: int | None) -> None:
    now = int(time.time())
    with get_pool().connection() as conn:
        conn.execute(
            """
            INSERT INTO players (torn_player_id, name, faction_id, last_seen_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (torn_player_id) DO UPDATE
                SET name = excluded.name, faction_id = excluded.faction_id, last_seen_at = excluded.last_seen_at
            """,
            (torn_player_id, name, faction_id, now),
        )
    get_player.clear()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_player(torn_player_id: int) -> dict | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT * FROM players WHERE torn_player_id = %s", (torn_player_id,)
        ).fetchone()
    return row


def mark_trial_used(torn_player_id: int, started_at: int) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "UPDATE players SET trial_used_at = %s WHERE torn_player_id = %s AND trial_used_at IS NULL",
            (started_at, torn_player_id),
        )
    get_player.clear()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_license(scope: str, key: int) -> dict | None:
    with get_pool().connection() as conn:
        if scope == "individual":
            row = conn.execute(
                "SELECT * FROM licenses WHERE scope = 'individual' AND torn_player_id = %s", (key,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM licenses WHERE scope = %s AND group_id = %s", (scope, key)
            ).fetchone()
    return row


def upsert_license(
    scope: str, key: int, premium_until: int, origin: str, last_payment_torn_log_id: str | None
) -> None:
    now = int(time.time())
    with get_pool().connection() as conn:
        if scope == "individual":
            conn.execute(
                """
                INSERT INTO licenses
                    (scope, torn_player_id, group_id, premium_until, activated_at, origin, last_payment_torn_log_id)
                VALUES ('individual', %s, NULL, %s, %s, %s, %s)
                ON CONFLICT (torn_player_id) WHERE scope = 'individual' DO UPDATE
                    SET premium_until = excluded.premium_until, origin = excluded.origin,
                        last_payment_torn_log_id = excluded.last_payment_torn_log_id
                """,
                (key, premium_until, now, origin, last_payment_torn_log_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO licenses
                    (scope, torn_player_id, group_id, premium_until, activated_at, origin, last_payment_torn_log_id)
                VALUES (%s, NULL, %s, %s, %s, %s, %s)
                ON CONFLICT (scope, group_id) WHERE scope = 'faction' DO UPDATE
                    SET premium_until = excluded.premium_until, origin = excluded.origin,
                        last_payment_torn_log_id = excluded.last_payment_torn_log_id
                """,
                (scope, key, premium_until, now, origin, last_payment_torn_log_id),
            )
    _invalidate_license_caches()


def revoke_license(scope: str, key: int) -> bool:
    with get_pool().connection() as conn:
        if scope == "individual":
            cur = conn.execute(
                "DELETE FROM licenses WHERE scope = 'individual' AND torn_player_id = %s", (key,)
            )
        else:
            cur = conn.execute(
                "DELETE FROM licenses WHERE scope = %s AND group_id = %s", (scope, key)
            )
    _invalidate_license_caches()
    return cur.rowcount > 0


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def list_lifetime_grants() -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT * FROM licenses WHERE origin = 'lifetime' ORDER BY scope, activated_at"
        ).fetchall()
    return rows


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def count_lifetime_individual(player_ids: list[int]) -> int:
    if not player_ids:
        return 0
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM licenses "
            "WHERE scope = 'individual' AND origin = 'lifetime' AND torn_player_id = ANY(%s)",
            (player_ids,),
        ).fetchone()
    return row["c"]


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_credited_payment_ids(payer_player_id: int) -> set[str]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT torn_log_id FROM credited_payments WHERE payer_player_id = %s", (payer_player_id,)
        ).fetchall()
    return {row["torn_log_id"] for row in rows}


def record_credited_payment(
    torn_log_id: str, payer_player_id: int, credited_scope: str, credited_group_id: int | None, weeks_granted: int
) -> None:
    now = int(time.time())
    with get_pool().connection() as conn:
        conn.execute(
            """
            INSERT INTO credited_payments
                (torn_log_id, payer_player_id, credited_scope, credited_group_id, weeks_granted, credited_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (torn_log_id, payer_player_id) DO NOTHING
            """,
            (torn_log_id, payer_player_id, credited_scope, credited_group_id, weeks_granted, now),
        )
    get_credited_payment_ids.clear()


def ensure_player_seeded(torn_player_id: int) -> None:
    _seed_checklist_if_missing(torn_player_id)
    _seed_categories_if_missing(torn_player_id)


def _seed_categories_if_missing(torn_player_id: int) -> None:
    with get_pool().connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM categories WHERE torn_player_id = %s", (torn_player_id,)
        ).fetchone()["c"]
        if count > 0:
            return
        for name in SEED_CATEGORIES:
            conn.execute(
                "INSERT INTO categories (torn_player_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (torn_player_id, name),
            )


def _seed_checklist_if_missing(torn_player_id: int) -> None:
    with get_pool().connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM checklist_tasks WHERE torn_player_id = %s", (torn_player_id,)
        ).fetchone()["c"]
        if count > 0:
            return
        now = int(time.time())
        for task in SEED_TASKS:
            conn.execute(
                """
                INSERT INTO checklist_tasks
                    (torn_player_id, title, description, repeat_type, repeat_interval_days,
                     created_at, last_completed_at, is_done_current_cycle)
                VALUES (%s, %s, %s, %s, %s, %s, NULL, FALSE)
                """,
                (
                    torn_player_id, task["title"], task["description"], task["repeat_type"],
                    task["repeat_interval_days"], now,
                ),
            )


def insert_snapshot(torn_player_id: int, fields: dict) -> int:
    columns = [
        "synced_at", "money_onhand", "money_points", "vault_amount", "bank_amount",
        "energy_current", "energy_maximum", "nerve_current", "nerve_maximum",
        "happy_current", "happy_maximum", "networth", *NETWORTH_BREAKDOWN_COLUMNS,
        "refills_total", "nerverefills_total", "energydrinkused_total", "xantaken_total",
        "war_mode_active", "note",
    ]
    values = [torn_player_id] + [fields.get(c) for c in columns]
    placeholders = ", ".join(["%s"] * len(values))
    with get_pool().connection() as conn:
        row = conn.execute(
            f"INSERT INTO api_snapshots (torn_player_id, {', '.join(columns)}) "
            f"VALUES ({placeholders}) RETURNING id",
            values,
        ).fetchone()
    _invalidate_log_caches()
    return row["id"]


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_snapshots(torn_player_id: int, start_ts: int | None = None, end_ts: int | None = None) -> list[dict]:
    query = "SELECT * FROM api_snapshots WHERE torn_player_id = %s"
    params = [torn_player_id]
    if start_ts is not None:
        query += " AND synced_at >= %s"
        params.append(start_ts)
    if end_ts is not None:
        query += " AND synced_at <= %s"
        params.append(end_ts)
    query += " ORDER BY synced_at ASC"
    with get_pool().connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return rows


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_latest_snapshot(torn_player_id: int) -> dict | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT * FROM api_snapshots WHERE torn_player_id = %s ORDER BY synced_at DESC LIMIT 1",
            (torn_player_id,),
        ).fetchone()
    return row


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_existing_torn_log_ids(torn_player_id: int) -> set[str]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT torn_log_id FROM log_entries WHERE torn_player_id = %s", (torn_player_id,)
        ).fetchall()
    return {row["torn_log_id"] for row in rows if row["torn_log_id"] is not None}


def clear_synced_data(torn_player_id: int) -> None:
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM log_entries WHERE torn_player_id = %s", (torn_player_id,))
        conn.execute("DELETE FROM api_snapshots WHERE torn_player_id = %s", (torn_player_id,))
        conn.execute("DELETE FROM category_rules WHERE torn_player_id = %s", (torn_player_id,))
        conn.execute(
            "DELETE FROM settings WHERE torn_player_id = %s AND key = 'last_sync_at'", (torn_player_id,)
        )
    _invalidate_log_caches()
    _invalidate_category_caches()
    get_setting.clear()


def update_snapshot_note(torn_player_id: int, snapshot_id: int, note: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "UPDATE api_snapshots SET note = %s WHERE id = %s AND torn_player_id = %s",
            (note, snapshot_id, torn_player_id),
        )
    _invalidate_log_caches()


def insert_log_entries(torn_player_id: int, snapshot_id: int, entries: list[dict]) -> None:
    if not entries:
        return
    with get_pool().connection() as conn:
        for entry in entries:
            conn.execute(
                """
                INSERT INTO log_entries
                    (torn_player_id, snapshot_id, torn_log_id, timestamp, category, title,
                     raw_text, amount, app_category, user_note)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (torn_player_id, torn_log_id) WHERE torn_log_id IS NOT NULL DO NOTHING
                """,
                (
                    torn_player_id,
                    snapshot_id,
                    entry.get("torn_log_id"),
                    entry.get("timestamp"),
                    entry.get("category"),
                    entry.get("title"),
                    entry.get("raw_text"),
                    entry.get("amount"),
                    entry.get("app_category", "Uncategorized"),
                    entry.get("user_note"),
                ),
            )
    _invalidate_log_caches()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_log_entries(torn_player_id: int, start_ts: int | None = None, end_ts: int | None = None) -> list[dict]:
    query = "SELECT * FROM log_entries WHERE torn_player_id = %s"
    params = [torn_player_id]
    if start_ts is not None:
        query += " AND timestamp >= %s"
        params.append(start_ts)
    if end_ts is not None:
        query += " AND timestamp <= %s"
        params.append(end_ts)
    query += " ORDER BY timestamp ASC"
    with get_pool().connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return rows


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_log_entry_timestamp_range(torn_player_id: int) -> tuple[int, int] | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT MIN(timestamp) AS min_ts, MAX(timestamp) AS max_ts FROM log_entries WHERE torn_player_id = %s",
            (torn_player_id,),
        ).fetchone()
    if row is None or row["min_ts"] is None:
        return None
    return row["min_ts"], row["max_ts"]


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_entries_by_category(torn_player_id: int, app_category: str, limit: int | None = None) -> list[dict]:
    query = "SELECT * FROM log_entries WHERE torn_player_id = %s AND app_category = %s ORDER BY timestamp DESC"
    params = [torn_player_id, app_category]
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
    with get_pool().connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return rows


def get_uncategorized_log_entries(torn_player_id: int, limit: int | None = None) -> list[dict]:
    return get_entries_by_category(torn_player_id, "Uncategorized", limit=limit)


def update_log_entry_category(torn_player_id: int, entry_id: int, app_category: str, user_note: str | None) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "UPDATE log_entries SET app_category = %s, user_note = %s WHERE id = %s AND torn_player_id = %s",
            (app_category, user_note, entry_id, torn_player_id),
        )
    _invalidate_log_caches()


def bulk_categorize_by_title(
    torn_player_id: int, title: str, app_category: str, exclude_entry_id: int | None = None
) -> int:
    with get_pool().connection() as conn:
        cur = conn.execute(
            "UPDATE log_entries SET app_category = %s "
            "WHERE torn_player_id = %s AND title = %s AND app_category = 'Uncategorized' AND id != %s",
            (app_category, torn_player_id, title, exclude_entry_id or -1),
        )
        updated = cur.rowcount
    _invalidate_log_caches()
    return updated


def upsert_category_rule(torn_player_id: int, title: str, app_category: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO category_rules (torn_player_id, title, app_category) VALUES (%s, %s, %s) "
            "ON CONFLICT (torn_player_id, title) DO UPDATE SET app_category = excluded.app_category",
            (torn_player_id, title, app_category),
        )
    _invalidate_category_caches()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_all_category_rules(torn_player_id: int) -> dict[str, str]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT title, app_category FROM category_rules WHERE torn_player_id = %s", (torn_player_id,)
        ).fetchall()
    return {row["title"]: row["app_category"] for row in rows}


def reassign_category(torn_player_id: int, title: str, from_category: str, to_category: str) -> int:
    with get_pool().connection() as conn:
        cur = conn.execute(
            "UPDATE log_entries SET app_category = %s "
            "WHERE torn_player_id = %s AND title = %s AND app_category = %s",
            (to_category, torn_player_id, title, from_category),
        )
        updated = cur.rowcount
    _invalidate_log_caches()
    return updated


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def list_categories(torn_player_id: int) -> list[str]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT name FROM categories WHERE torn_player_id = %s ORDER BY name", (torn_player_id,)
        ).fetchall()
    return [row["name"] for row in rows]


def add_category(torn_player_id: int, name: str) -> bool:
    with get_pool().connection() as conn:
        cur = conn.execute(
            "INSERT INTO categories (torn_player_id, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (torn_player_id, name),
        )
        added = cur.rowcount > 0
    _invalidate_category_caches()
    return added


def delete_category(torn_player_id: int, name: str) -> bool:
    with get_pool().connection() as conn:
        in_use = conn.execute(
            "SELECT COUNT(*) AS c FROM log_entries WHERE torn_player_id = %s AND app_category = %s",
            (torn_player_id, name),
        ).fetchone()["c"]
        if in_use > 0:
            return False
        conn.execute(
            "DELETE FROM categories WHERE torn_player_id = %s AND name = %s", (torn_player_id, name)
        )
    _invalidate_category_caches()
    return True


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_category_counts(torn_player_id: int) -> dict[str, int]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT app_category, COUNT(*) AS c FROM log_entries WHERE torn_player_id = %s GROUP BY app_category",
            (torn_player_id,),
        ).fetchall()
    return {row["app_category"]: row["c"] for row in rows}


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_title_category_summary(torn_player_id: int, filter_category: str | None = None) -> list[dict]:
    query = "SELECT title, app_category, COUNT(*) AS c FROM log_entries WHERE torn_player_id = %s"
    params = [torn_player_id]
    if filter_category:
        query += " AND app_category = %s"
        params.append(filter_category)
    query += " GROUP BY title, app_category ORDER BY title"
    with get_pool().connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return rows


def recategorize_period(torn_player_id: int, start_ts: int, end_ts: int, app_category: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "UPDATE log_entries SET app_category = %s "
            "WHERE torn_player_id = %s AND timestamp >= %s AND timestamp <= %s",
            (app_category, torn_player_id, start_ts, end_ts),
        )
    _invalidate_log_caches()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def get_setting(torn_player_id: int, key: str, default: str | None = None) -> str | None:
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE torn_player_id = %s AND key = %s", (torn_player_id, key)
        ).fetchone()
    if row is None:
        return default
    return row["value"]


def set_setting(torn_player_id: int, key: str, value: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO settings (torn_player_id, key, value) VALUES (%s, %s, %s) "
            "ON CONFLICT (torn_player_id, key) DO UPDATE SET value = excluded.value",
            (torn_player_id, key, value),
        )
    get_setting.clear()


@st.cache_data(ttl=CACHE_TTL_SECONDS)
def list_checklist_tasks(torn_player_id: int) -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT * FROM checklist_tasks WHERE torn_player_id = %s ORDER BY created_at ASC",
            (torn_player_id,),
        ).fetchall()
    return rows


def create_checklist_task(
    torn_player_id: int, title: str, description: str, repeat_type: str, repeat_interval_days: int | None
) -> int:
    now = int(time.time())
    with get_pool().connection() as conn:
        row = conn.execute(
            """
            INSERT INTO checklist_tasks
                (torn_player_id, title, description, repeat_type, repeat_interval_days,
                 created_at, last_completed_at, is_done_current_cycle)
            VALUES (%s, %s, %s, %s, %s, %s, NULL, FALSE)
            RETURNING id
            """,
            (torn_player_id, title, description, repeat_type, repeat_interval_days, now),
        ).fetchone()
    _invalidate_checklist_cache()
    return row["id"]


def update_checklist_task(
    torn_player_id: int,
    task_id: int,
    title: str,
    description: str,
    repeat_type: str,
    repeat_interval_days: int | None,
) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            """
            UPDATE checklist_tasks
            SET title = %s, description = %s, repeat_type = %s, repeat_interval_days = %s
            WHERE id = %s AND torn_player_id = %s
            """,
            (title, description, repeat_type, repeat_interval_days, task_id, torn_player_id),
        )
    _invalidate_checklist_cache()


def delete_checklist_task(torn_player_id: int, task_id: int) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "DELETE FROM checklist_tasks WHERE id = %s AND torn_player_id = %s", (task_id, torn_player_id)
        )
    _invalidate_checklist_cache()


def set_task_done(torn_player_id: int, task_id: int, done: bool, completed_at: int | None) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "UPDATE checklist_tasks SET is_done_current_cycle = %s, last_completed_at = %s "
            "WHERE id = %s AND torn_player_id = %s",
            (done, completed_at, task_id, torn_player_id),
        )
    _invalidate_checklist_cache()


def reset_task_cycle(torn_player_id: int, task_id: int) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "UPDATE checklist_tasks SET is_done_current_cycle = FALSE WHERE id = %s AND torn_player_id = %s",
            (task_id, torn_player_id),
        )
    _invalidate_checklist_cache()
