import datetime
import time

import streamlit as st

import auth
import db
import licensing
import theme
import torn_api

st.set_page_config(page_title="Settings - Torn Cashflow", page_icon="\U00002699", layout="wide")
theme.inject_theme()
db.init_db()
st.title("Settings")


def show_flash(key: str) -> None:
    flash = st.session_state.pop(key, None)
    if flash is not None:
        kind, message = flash
        getattr(st, kind)(message)


st.subheader("Torn API Key")
st.caption(
    "Create a Full Access key at torn.com → Settings → API. Paste it below each session — "
    "it's kept only in this browser session, never written to a shared file, and never logged."
)

player = auth.get_current_player()
if player is not None:
    st.write(f"Signed in as **{player.name}** (player id {player.player_id}), key `{auth.mask_key(player.api_key)}`.")

show_flash("settings_api_key_flash")

with st.form("api_key_form"):
    new_key = st.text_input("Full Access API key", type="password")
    submitted = st.form_submit_button("Save key")
    if submitted:
        if not new_key.strip():
            st.error("Enter a key before saving.")
        else:
            try:
                resolved = auth.resolve_player(new_key.strip())
                st.session_state["settings_api_key_flash"] = (
                    "success",
                    f"Signed in as {resolved.name} (player id {resolved.player_id}).",
                )
                st.rerun()
            except torn_api.TornAPIError as exc:
                st.error(f"Torn API error: {exc}")
            except torn_api.TornNetworkError as exc:
                st.error(f"Network error: {exc}")

if player is not None and st.button("Log out"):
    auth.clear_api_key()
    st.rerun()

if player is None:
    st.stop()

st.divider()
st.subheader("War Mode")
war_mode_active = db.get_setting(player.player_id, "war_mode_active", "0") == "1"
new_state = st.toggle("War Mode active", value=war_mode_active)
if new_state != war_mode_active:
    db.set_setting(player.player_id, "war_mode_active", "1" if new_state else "0")
    if new_state:
        db.set_setting(player.player_id, "war_mode_started_at", str(int(time.time())))
    st.rerun()

st.caption(
    "Turn this on during a ranked war. It drives auto-categorization of log entries as 'Ranked War' during sync, "
    "and controls which 'On War Days' checklist tasks are shown/reset."
)

st.divider()
st.subheader("Premium / License")

show_flash("settings_trial_flash")
show_flash("settings_payment_flash")

status = licensing.get_premium_status(player)
SOURCE_LABELS = {"trial": "your free trial", "individual": "your payment", "faction": "your faction"}

if status.is_premium:
    expiry_display = datetime.datetime.utcfromtimestamp(status.premium_until).strftime("%Y-%m-%d %H:%M UTC")
    st.success(f"Premium active via {SOURCE_LABELS.get(status.source, status.source)}, until {expiry_display}.")
else:
    st.info("Free tier.")

dev_player_id = int(st.secrets["DEV_TORN_PLAYER_ID"])
st.write(f"Send **1 Xanax** to Torn player **[{dev_player_id}]** for 4 weeks of Premium.")

if player.faction_id:
    st.caption(
        "Faction leaders: bulk-send Xanax to cover your whole faction at a discount — "
        "click **Check my payment now** below and it'll tell you the required amount if it's short."
    )

player_row = db.get_player(player.player_id)
trial_used = bool(player_row and player_row["trial_used_at"] is not None)

if not trial_used and not status.is_premium:
    if st.button("Start my 7-day free trial"):
        trial_result = licensing.start_free_trial(player)
        if trial_result.started:
            expiry_display = datetime.datetime.utcfromtimestamp(trial_result.premium_until).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
            st.session_state["settings_trial_flash"] = ("success", f"Trial started! Premium until {expiry_display}.")
        else:
            st.session_state["settings_trial_flash"] = ("error", trial_result.reason)
        st.rerun()

if st.button("Check my payment now"):
    messages = []
    if player.faction_id:
        group_result = licensing.scan_and_activate_group_payment(player)
        messages.append(group_result.message)
    individual_result = licensing.scan_and_activate_payment(player)
    if individual_result.credited_count > 0:
        messages.append(
            f"Credited {individual_result.weeks_added} week(s) from {individual_result.credited_count} payment(s)."
        )
    elif not player.faction_id or not messages:
        messages.append("No new qualifying payment found in the last 7 days.")
    st.session_state["settings_payment_flash"] = ("info", "  \n".join(messages))
    st.rerun()
