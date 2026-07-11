from fastapi import Depends, Request

from . import db, licensing, security
from .errors import ApiError
from .models import CurrentPlayer


def get_current_player(request: Request) -> CurrentPlayer:
    token = request.cookies.get("session_token")
    if not token:
        raise ApiError(401, "Not signed in.", "not_authenticated")

    payload = security.decode_session_token(token)
    if payload is None:
        raise ApiError(401, "Session expired or invalid.", "not_authenticated")

    player_row = db.get_player(payload["playerId"])
    if player_row is None or not player_row.get("api_key"):
        raise ApiError(401, "Not signed in.", "not_authenticated")

    invalidated_at = player_row.get("key_invalidated_at")
    if invalidated_at is not None and payload["issuedAt"] < invalidated_at:
        raise ApiError(401, "Your Torn API key stopped working. Please sign in again.", "key_invalidated")

    api_key = security.decrypt_api_key(player_row["api_key"])
    return CurrentPlayer(
        player_id=player_row["torn_player_id"],
        name=player_row["name"],
        faction_id=player_row["faction_id"],
        api_key=api_key,
    )


def require_premium(player: CurrentPlayer = Depends(get_current_player)) -> CurrentPlayer:
    status = licensing.get_premium_status(player)
    if not status.is_premium:
        raise ApiError(403, "This feature requires Premium.", "premium_required")
    return player


def require_admin(player: CurrentPlayer = Depends(get_current_player)) -> CurrentPlayer:
    if not licensing.is_admin(player):
        raise ApiError(403, "Admin only.", "admin_required")
    return player
