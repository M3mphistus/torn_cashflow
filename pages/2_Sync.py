import datetime
import time

import streamlit as st

import auth
import calculations
import db
import licensing
import theme
import torn_api

st.set_page_config(page_title="Sync - Torn Cashflow", page_icon="\U0001F504", layout="wide")
theme.inject_theme()
db.init_db()
st.title("Sync")

player = auth.get_current_player()
if player is None:
    st.warning("Paste your Torn Full Access API key in Settings first.")
    st.stop()

api_key = player.api_key
last_sync_at = db.get_setting(player.player_id, "last_sync_at")
war_mode_active = db.get_setting(player.player_id, "war_mode_active", "0") == "1"

if last_sync_at:
    last_sync_display = datetime.datetime.utcfromtimestamp(int(last_sync_at)).strftime("%Y-%m-%d %H:%M UTC")
    st.write(f"Last sync: {last_sync_display}")
else:
    st.write("No sync has happened yet.")

st.write(f"War Mode is currently **{'ON' if war_mode_active else 'OFF'}** (change it in Settings).")


def categorize_and_insert(snapshot_id: int, log_entries: list[dict], war_mode_active: bool) -> list[dict]:
    category_rules = db.get_all_category_rules(player.player_id)
    prepared_entries = []
    for entry in log_entries:
        title = entry.get("title")
        if title and title in category_rules:
            app_category = category_rules[title]
        else:
            app_category = calculations.auto_categorize(title, entry.get("category"), war_mode_active)
        if app_category == "Uncategorized" and entry.get("amount") is None:
            app_category = calculations.IGNORED_CATEGORY
        prepared_entries.append({**entry, "app_category": app_category})
    db.insert_log_entries(player.player_id, snapshot_id, prepared_entries)
    return prepared_entries


if st.button("Sync now", type="primary"):
    now_ts = int(time.time())
    from_ts = int(last_sync_at) if last_sync_at else now_ts - 7 * 86400

    try:
        with st.spinner("Fetching bars..."):
            bars = torn_api.get_bars(api_key)
        with st.spinner("Fetching money..."):
            money = torn_api.get_money(api_key)
        with st.spinner("Fetching personal stats..."):
            stats = torn_api.get_personalstats(api_key)
        with st.spinner("Fetching log..."):
            log_entries = torn_api.get_log(api_key, from_ts, now_ts)
    except torn_api.TornAPIError as exc:
        st.error(f"Torn API error: {exc}")
        st.stop()
    except torn_api.TornNetworkError as exc:
        st.error(f"Network error: {exc}")
        st.stop()

    snapshot_fields = {
        "synced_at": now_ts,
        "war_mode_active": war_mode_active,
        **bars,
        **money,
        **stats,
    }
    snapshot_id = db.insert_snapshot(player.player_id, snapshot_fields)
    prepared_entries = categorize_and_insert(snapshot_id, log_entries, war_mode_active)

    db.set_setting(player.player_id, "last_sync_at", str(now_ts))

    st.success(f"Sync complete. Stored 1 snapshot and {len(prepared_entries)} log entries.")
    st.rerun()

st.divider()
licensing.render_heading_with_badge("###", "Full History Sync")
st.caption(
    "Fetches your current bars/money/stats plus your complete log history by paging backward through "
    "the Torn API, bypassing its ~100-entries-per-call cap. This uses many API requests and can take a "
    "while for accounts with a long history."
)
if not licensing.get_premium_status(player).is_premium:
    st.caption(
        "Requires Premium — clicking below will show your options (trial, Xanax payment, or faction bulk)."
    )

if st.button("Get all Data"):
    if not licensing.require_premium("Get all Data (full history sync)", player):
        st.stop()

    now_ts = int(time.time())

    try:
        with st.spinner("Fetching bars..."):
            bars = torn_api.get_bars(api_key)
        with st.spinner("Fetching money..."):
            money = torn_api.get_money(api_key)
        with st.spinner("Fetching personal stats..."):
            stats = torn_api.get_personalstats(api_key)
    except torn_api.TornAPIError as exc:
        st.error(f"Torn API error: {exc}")
        st.stop()
    except torn_api.TornNetworkError as exc:
        st.error(f"Network error: {exc}")
        st.stop()

    snapshot_fields = {
        "synced_at": now_ts,
        "war_mode_active": war_mode_active,
        **bars,
        **money,
        **stats,
    }
    snapshot_id = db.insert_snapshot(player.player_id, snapshot_fields)

    progress_placeholder = st.empty()

    def report_progress(count: int, oldest_ts: int, page: int) -> None:
        oldest_display = datetime.datetime.utcfromtimestamp(oldest_ts).strftime("%Y-%m-%d %H:%M UTC")
        progress_placeholder.info(f"Page {page}: {count} log entries fetched so far (oldest so far: {oldest_display})...")

    try:
        all_log_entries = torn_api.get_full_log(api_key, progress_callback=report_progress)
    except torn_api.TornAPIError as exc:
        st.error(f"Torn API error while paging log: {exc}")
        st.stop()
    except torn_api.TornNetworkError as exc:
        st.error(f"Network error while paging log: {exc}")
        st.stop()

    existing_ids = db.get_existing_torn_log_ids(player.player_id)
    new_entries = [e for e in all_log_entries if e["torn_log_id"] not in existing_ids]
    categorize_and_insert(snapshot_id, new_entries, war_mode_active)

    db.set_setting(player.player_id, "last_sync_at", str(now_ts))
    progress_placeholder.empty()

    already_stored = len(all_log_entries) - len(new_entries)
    st.success(
        f"Full history sync complete. Stored 1 snapshot, {len(new_entries)} new log entries "
        f"({already_stored} were already stored)."
    )
    st.rerun()

st.divider()
st.subheader("Period Note")

latest = db.get_latest_snapshot(player.player_id)
if latest is not None:
    note = st.text_area("Note for the latest sync period", value=latest["note"] or "")
    if st.button("Save note"):
        db.update_snapshot_note(player.player_id, latest["id"], note)
        st.success("Note saved.")
        st.rerun()

ENTRY_LIST_DISPLAY_LIMIT = 25

st.divider()
st.subheader("Uncategorized Log Entries")

total_uncategorized = db.get_category_counts(player.player_id).get("Uncategorized", 0)
uncategorized = db.get_uncategorized_log_entries(player.player_id, limit=ENTRY_LIST_DISPLAY_LIMIT)
if not uncategorized:
    st.info("No uncategorized log entries.")
else:
    if total_uncategorized > len(uncategorized):
        st.caption(
            f"Showing the {len(uncategorized)} most recent of {total_uncategorized} uncategorized entries. "
            "Use the **Categories** page to bulk-recategorize the rest by title."
        )
    category_options = db.list_categories(player.player_id) + ["Uncategorized"]
    for entry in uncategorized:
        with st.container(border=True):
            ts_display = datetime.datetime.utcfromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M UTC")
            amount_display = f"${entry['amount']:,.0f}" if entry["amount"] is not None else "no amount detected"
            st.write(f"**{entry['title'] or 'Unknown event'}** — {ts_display} — {amount_display}")
            if entry["raw_text"]:
                st.caption(entry["raw_text"])
            cols = st.columns([3, 3, 1, 1])
            with cols[0]:
                selected_category = st.selectbox(
                    "Category", category_options, key=f"cat_{entry['id']}", index=len(category_options) - 1
                )
            with cols[1]:
                user_note = st.text_input("Note", value=entry["user_note"] or "", key=f"note_{entry['id']}")
            with cols[2]:
                st.write("")
                st.write("")
                if st.button("Save", key=f"save_{entry['id']}"):
                    db.update_log_entry_category(player.player_id, entry["id"], selected_category, user_note)
                    if entry["title"]:
                        db.upsert_category_rule(player.player_id, entry["title"], selected_category)
                        db.bulk_categorize_by_title(
                            player.player_id, entry["title"], selected_category, exclude_entry_id=entry["id"]
                        )
                    st.rerun()
            with cols[3]:
                st.write("")
                st.write("")
                if st.button("Ignore", key=f"ignore_{entry['id']}"):
                    db.update_log_entry_category(player.player_id, entry["id"], calculations.IGNORED_CATEGORY, user_note)
                    if entry["title"]:
                        db.upsert_category_rule(player.player_id, entry["title"], calculations.IGNORED_CATEGORY)
                        db.bulk_categorize_by_title(
                            player.player_id, entry["title"], calculations.IGNORED_CATEGORY, exclude_entry_id=entry["id"]
                        )
                    st.rerun()

st.divider()
st.subheader("Ignored Log Entries")

total_ignored = db.get_category_counts(player.player_id).get(calculations.IGNORED_CATEGORY, 0)
ignored_entries = db.get_entries_by_category(
    player.player_id, calculations.IGNORED_CATEGORY, limit=ENTRY_LIST_DISPLAY_LIMIT
)
if not ignored_entries:
    st.caption("No ignored log entries.")
else:
    expander_label = f"{len(ignored_entries)} most recent of {total_ignored} ignored entries"
    with st.expander(expander_label):
        if total_ignored > len(ignored_entries):
            st.caption("Use the **Categories** page to review or bulk-restore the rest by title.")
        for entry in ignored_entries:
            ts_display = datetime.datetime.utcfromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M UTC")
            cols = st.columns([5, 1])
            with cols[0]:
                st.write(f"**{entry['title'] or 'Unknown event'}** — {ts_display}")
            with cols[1]:
                if st.button("Restore", key=f"restore_{entry['id']}"):
                    db.update_log_entry_category(player.player_id, entry["id"], "Uncategorized", entry["user_note"])
                    st.rerun()

st.divider()
st.subheader("Danger Zone")
st.caption(
    "Deletes all your synced snapshots, log entries, and learned category rules from the database. "
    "Your checklist tasks and War Mode setting are not affected. This cannot be undone."
)

confirm_clear = st.checkbox("I understand this permanently deletes all synced data")
if st.button("Clear DB", disabled=not confirm_clear):
    db.clear_synced_data(player.player_id)
    st.success("All synced data cleared.")
    st.rerun()
