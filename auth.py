from dataclasses import dataclass, field

import streamlit as st
from streamlit_cookies_controller import CookieController

import db
import torn_api

SESSION_KEY_API_KEY = "torn_api_key"
SESSION_KEY_PLAYER = "current_player"
SESSION_KEY_AUTH_ERROR = "auth_error"
SESSION_KEY_COOKIE_ATTEMPTED = "auth_cookie_login_attempted"

COOKIE_CONTROLLER_KEY = "torn_cookie_controller"
COOKIE_NAME = "torn_api_key"
COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 400  # ~400 days — browsers (Chrome, etc.) cap cookie
# lifetime at 400 days regardless of what's requested, so this is effectively "no expiry":
# the longest a "stay signed in" cookie can practically live is renewed on every login anyway.

# The exact Torn selections torn_api.py reads: basic profile (identity/faction), bars,
# money, personalstats (networth + breakdown), and log (categorized history + Xanax
# payment detection). This deep-links to Torn's "Custom" key builder with exactly these
# pre-checked, so visitors never have to create a blanket Full Access key.
CUSTOM_KEY_TITLE = "Torn Cashflow Dashboard"
CUSTOM_KEY_SELECTIONS = "basic,profile,bars,money,personalstats,log"
CUSTOM_KEY_URL = (
    "https://www.torn.com/preferences.php#tab=api?step=addNewKey"
    f"&title={CUSTOM_KEY_TITLE.replace(' ', '%20')}&user={CUSTOM_KEY_SELECTIONS}"
)


def _cookies() -> CookieController:
    return CookieController(key=COOKIE_CONTROLLER_KEY)


@dataclass
class CurrentPlayer:
    player_id: int
    name: str | None
    faction_id: int | None
    api_key: str = field(repr=False)


def mask_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 4:
        return "*" * len(api_key)
    return "*" * (len(api_key) - 4) + api_key[-4:]


def set_api_key(api_key: str, remember: bool = True) -> None:
    st.session_state[SESSION_KEY_API_KEY] = api_key
    st.session_state.pop(SESSION_KEY_PLAYER, None)
    st.session_state.pop(SESSION_KEY_AUTH_ERROR, None)
    if remember:
        _cookies().set(COOKIE_NAME, api_key, max_age=COOKIE_MAX_AGE_SECONDS)


def clear_api_key() -> None:
    st.session_state.pop(SESSION_KEY_API_KEY, None)
    st.session_state.pop(SESSION_KEY_PLAYER, None)
    st.session_state.pop(SESSION_KEY_AUTH_ERROR, None)
    st.session_state.pop(SESSION_KEY_COOKIE_ATTEMPTED, None)
    _cookies().remove(COOKIE_NAME)


def resolve_player(api_key: str, remember: bool = True) -> CurrentPlayer:
    profile = torn_api.get_basic_profile(api_key)
    player = CurrentPlayer(
        player_id=profile["player_id"],
        name=profile["name"],
        faction_id=profile["faction_id"],
        api_key=api_key,
    )
    db.upsert_player(player.player_id, player.name, player.faction_id)
    db.ensure_player_seeded(player.player_id)
    st.session_state[SESSION_KEY_API_KEY] = api_key
    st.session_state[SESSION_KEY_PLAYER] = player
    if remember:
        _cookies().set(COOKIE_NAME, api_key, max_age=COOKIE_MAX_AGE_SECONDS)
    return player


def get_current_player() -> CurrentPlayer | None:
    """Session-cached player, falling back to auto-login from the remembered
    browser cookie so a visitor stays signed in across reloads/new sessions.
    """
    cached = st.session_state.get(SESSION_KEY_PLAYER)
    if cached is not None:
        return cached

    if st.session_state.get(SESSION_KEY_COOKIE_ATTEMPTED):
        return None

    saved_key = _cookies().get(COOKIE_NAME)
    if not saved_key:
        return None

    st.session_state[SESSION_KEY_COOKIE_ATTEMPTED] = True
    try:
        return resolve_player(saved_key)
    except (torn_api.TornAPIError, torn_api.TornNetworkError):
        _cookies().remove(COOKIE_NAME)
        return None


def get_saved_api_key() -> str | None:
    saved = st.session_state.get(SESSION_KEY_API_KEY)
    if saved:
        return saved
    return _cookies().get(COOKIE_NAME)


def get_auth_error() -> str | None:
    return st.session_state.get(SESSION_KEY_AUTH_ERROR)


def set_auth_error(message: str) -> None:
    st.session_state[SESSION_KEY_AUTH_ERROR] = message
