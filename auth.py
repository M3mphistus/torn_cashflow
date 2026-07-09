from dataclasses import dataclass, field

import streamlit as st

import db
import torn_api

SESSION_KEY_API_KEY = "torn_api_key"
SESSION_KEY_PLAYER = "current_player"
SESSION_KEY_AUTH_ERROR = "auth_error"


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


def set_api_key(api_key: str) -> None:
    st.session_state[SESSION_KEY_API_KEY] = api_key
    st.session_state.pop(SESSION_KEY_PLAYER, None)
    st.session_state.pop(SESSION_KEY_AUTH_ERROR, None)


def clear_api_key() -> None:
    st.session_state.pop(SESSION_KEY_API_KEY, None)
    st.session_state.pop(SESSION_KEY_PLAYER, None)
    st.session_state.pop(SESSION_KEY_AUTH_ERROR, None)


def resolve_player(api_key: str) -> CurrentPlayer:
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
    return player


def get_current_player() -> CurrentPlayer | None:
    return st.session_state.get(SESSION_KEY_PLAYER)


def get_saved_api_key() -> str | None:
    return st.session_state.get(SESSION_KEY_API_KEY)


def get_auth_error() -> str | None:
    return st.session_state.get(SESSION_KEY_AUTH_ERROR)


def set_auth_error(message: str) -> None:
    st.session_state[SESSION_KEY_AUTH_ERROR] = message
