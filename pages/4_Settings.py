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
    "Create a Full Access key at torn.com → Settings → API. It's remembered in this browser "
    "(via a cookie on this device) so you stay signed in across visits — never written to a "
    "shared file, and never logged. Use **Log out** below to forget it on this device."
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
SOURCE_LABELS = {
    "trial": "your free trial",
    "individual": "your payment",
    "faction": "your faction",
    "lifetime_individual": "a lifetime grant",
    "lifetime_faction": "your faction's lifetime grant",
}

if status.is_premium:
    if status.premium_until >= licensing.LIFETIME_SENTINEL_TS:
        st.success(f"Premium active via {SOURCE_LABELS.get(status.source, status.source)} — forever.")
    else:
        expiry_display = datetime.datetime.utcfromtimestamp(status.premium_until).strftime("%Y-%m-%d %H:%M UTC")
        st.success(f"Premium active via {SOURCE_LABELS.get(status.source, status.source)}, until {expiry_display}.")
else:
    st.info("Free tier.")

st.write(f"Send **1 Xanax** to {licensing.dev_profile_link()} for 4 weeks of Premium.")

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

st.markdown("##### Pay for Premium")

pay_options = ["Just myself"]
if player.faction_id:
    pay_options.append("My whole faction (bulk)")

pay_mode = st.radio("Who are you paying for?", pay_options, horizontal=True, label_visibility="collapsed")

if pay_mode == "My whole faction (bulk)":
    preview = licensing.get_faction_requirement_preview(player)
    if preview is None:
        st.warning("Could not read your faction's member list right now — try again shortly.")
    else:
        discount_display = f"{preview.discount_pct:.0%}" if preview.discount_pct else "no discount yet"
        covered_note = (
            f" ({preview.lifetime_covered_count} member(s) already have lifetime Premium and aren't counted in the amount)"
            if preview.lifetime_covered_count
            else ""
        )
        st.write(
            f"Your faction has **{preview.member_count}** members ({discount_display} bulk discount) — "
            f"send **{preview.required} Xanax** total to cover everyone for 4 weeks{covered_note}."
        )
else:
    st.caption("1 Xanax covers 4 weeks of Premium for your account only.")

if st.button("Check my payment now"):
    messages = []
    if pay_mode == "My whole faction (bulk)":
        group_result = licensing.scan_and_activate_group_payment(player)
        messages.append(group_result.message)
    else:
        individual_result = licensing.scan_and_activate_payment(player)
        if individual_result.credited_count > 0:
            messages.append(
                f"Credited {individual_result.weeks_added} week(s) from {individual_result.credited_count} payment(s)."
            )
        else:
            messages.append("No new qualifying payment found in the last 7 days.")
    st.session_state["settings_payment_flash"] = ("info", "  \n".join(messages))
    st.rerun()

if licensing.is_admin(player):
    st.divider()
    st.subheader("Admin: Lifetime Premium Grants")
    st.caption("Only visible to the developer account.")

    show_flash("settings_admin_flash")

    grant_scope = st.radio("Grant type", ["Individual player", "Faction"], horizontal=True, key="admin_grant_scope")
    grant_id = st.number_input(
        "Torn player ID" if grant_scope == "Individual player" else "Faction ID",
        min_value=1, step=1, value=None, key="admin_grant_id",
    )
    if st.button("Grant lifetime Premium"):
        if not grant_id:
            st.error("Enter an ID first.")
        else:
            scope_key = "individual" if grant_scope == "Individual player" else "faction"
            licensing.grant_lifetime(scope_key, int(grant_id))
            st.session_state["settings_admin_flash"] = (
                "success", f"Granted lifetime Premium to {grant_scope.lower()} {int(grant_id)}.",
            )
            st.rerun()

    grants = licensing.list_lifetime_grants()
    if grants:
        st.write("Current lifetime grants:")
        for grant in grants:
            key = grant["torn_player_id"] if grant["scope"] == "individual" else grant["group_id"]
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{grant['scope']}** — `{key}`")
            if col2.button("Revoke", key=f"revoke_{grant['scope']}_{key}"):
                licensing.revoke_lifetime(grant["scope"], key)
                st.session_state["settings_admin_flash"] = ("info", f"Revoked lifetime grant for {grant['scope']} {key}.")
                st.rerun()
    else:
        st.caption("No lifetime grants yet.")
