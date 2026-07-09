import datetime

import streamlit as st

import auth
import db
import theme

st.set_page_config(page_title="Torn Cashflow Dashboard", page_icon="\U0001F4B0", layout="wide")
theme.inject_theme()

db.init_db()

st.title("Torn Cashflow Dashboard")
st.write(
    "Cashflow, energy/nerve, and checklist tracking for Torn.com. Paste your own Torn "
    "Full Access API key in Settings each visit — nothing is stored beyond your browser session."
)

player = auth.get_current_player()
if player is None:
    st.warning("No API key entered yet this session. Open **Settings** in the sidebar to paste your Torn Full Access API key.")
else:
    st.success(f"Signed in as **{player.name}** (player id {player.player_id}).")
    latest = db.get_latest_snapshot(player.player_id)
    if latest is None:
        st.info("No sync data yet. Open **Sync** in the sidebar and click 'Sync now' to pull your first snapshot.")
    else:
        st.write(
            f"Last synced at: {datetime.datetime.utcfromtimestamp(latest['synced_at']).strftime('%Y-%m-%d %H:%M UTC')}"
        )

st.markdown(
    """
    Use the sidebar to navigate:
    - **Dashboard** — KPIs, charts, and the raw snapshot table.
    - **Sync** — pull fresh data from the Torn API and categorize log entries.
    - **Checklist** — recurring and one-off tasks.
    - **Categories** — manage categories and bulk-recategorize entries.
    - **Settings** — API key, War Mode toggle, and Premium/License status.
    """
)
