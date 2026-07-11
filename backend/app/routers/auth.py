from fastapi import APIRouter, Depends, Response

from .. import db, licensing, security, torn_api, torn_errors
from ..deps import get_current_player
from ..models import CurrentPlayer
from ..schemas.auth import LoginRequest, PlayerSessionResponse, player_to_dto, premium_status_to_dto
from ..errors import ApiError

router = APIRouter()


@router.post("/login")
def login(body: LoginRequest, response: Response) -> PlayerSessionResponse:
    api_key = body.api_key.strip()
    if not api_key:
        raise ApiError(400, "API key is required.", "invalid_request")

    try:
        profile = torn_api.get_basic_profile(api_key)
    except (torn_api.TornAPIError, torn_api.TornNetworkError) as exc:
        raise torn_errors.login_error(exc) from exc

    db.upsert_player(profile["player_id"], profile["name"], profile["faction_id"])
    db.ensure_player_seeded(profile["player_id"])
    db.set_player_api_key(profile["player_id"], security.encrypt_api_key(api_key))
    db.clear_key_invalidated(profile["player_id"])

    token = security.create_session_token(profile["player_id"])
    response.set_cookie(
        "session_token", token,
        httponly=True, secure=True, samesite="none", path="/",
        max_age=security.JWT_EXPIRY_SECONDS,
    )

    player = CurrentPlayer(profile["player_id"], profile["name"], profile["faction_id"], api_key)
    premium = licensing.get_premium_status(player)
    return PlayerSessionResponse(player=player_to_dto(player), premium=premium_status_to_dto(premium))


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie("session_token", path="/")


@router.get("/me")
def me(player: CurrentPlayer = Depends(get_current_player)) -> PlayerSessionResponse:
    premium = licensing.get_premium_status(player)
    return PlayerSessionResponse(player=player_to_dto(player), premium=premium_status_to_dto(premium))
