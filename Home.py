import datetime

import streamlit as st

import auth
import db
import licensing
import theme

st.set_page_config(page_title="Torn Cashflow Dashboard", page_icon="\U0001F4B0", layout="wide")
theme.inject_theme()

db.init_db()

st.caption("A SPEAKEASY LEDGER FOR TORN CITY")
st.title("Torn Cashflow Dashboard")
st.write(
    "Track your cashflow, energy/nerve spend, networth, and a recurring checklist — all pulled "
    "straight from your own Torn account. Create a scoped API key once in Settings and "
    "you'll stay signed in on this browser."
)

player = auth.get_current_player()
if player is None:
    st.warning("No API key on file for this browser yet.")
    st.page_link("pages/4_Settings.py", label="Open Settings to paste your key", icon="\U0001F511")
else:
    st.success(f"Signed in as **{player.name}** (player id {player.player_id}).")
    latest = db.get_latest_snapshot(player.player_id)
    if latest is None:
        st.info("No sync data yet.")
        st.page_link("pages/2_Sync.py", label="Go to Sync and pull your first snapshot", icon="\U0001F504")
    else:
        synced_display = datetime.datetime.utcfromtimestamp(latest["synced_at"]).strftime("%Y-%m-%d %H:%M UTC")
        st.write(f"Last synced at: {synced_display}")

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        st.subheader("Dashboard")
        st.caption("KPIs, cashflow-by-category, networth breakdown, and the raw snapshot table.")
        st.page_link("pages/1_Dashboard.py", label="Open Dashboard")
with col2:
    with st.container(border=True):
        st.subheader("Sync")
        st.caption("Pull fresh data from the Torn API and review auto-categorized log entries.")
        st.page_link("pages/2_Sync.py", label="Open Sync")
with col3:
    with st.container(border=True):
        st.subheader("Checklist")
        st.caption("Recurring and one-off tasks — daily refills, war prep, and more.")
        st.page_link("pages/3_Checklist.py", label="Open Checklist")

col4, col5 = st.columns(2)
with col4:
    with st.container(border=True):
        licensing.render_heading_with_badge("###", "Categories")
        st.caption("Manage categories and bulk-recategorize log entries by title.")
        st.page_link("pages/5_Categories.py", label="Open Categories")
with col5:
    with st.container(border=True):
        st.subheader("Settings")
        st.caption("API key, War Mode toggle, and your Premium/License status.")
        st.page_link("pages/4_Settings.py", label="Open Settings")

st.divider()
st.caption(
    "Free tier covers day-to-day tracking. Premium (full history sync, Categories, and automatic "
    "checklist resets) unlocks with a 7-day free trial or by sending Xanax in-game — see Settings."
)
st.caption(
    "This app is fully open source — [read the code on GitHub](https://github.com/M3mphistus/torn_cashflow). "
    "Not affiliated with or endorsed by Torn. See **Settings** for what data is accessed/stored and how to remove it."
)
st.caption(f"Feedback or suggestions? Send a Torn message to {licensing.dev_profile_link()} — see Settings.")
