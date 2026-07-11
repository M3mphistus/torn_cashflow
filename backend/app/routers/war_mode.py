import time

from fastapi import APIRouter, Depends

from .. import db
from ..deps import get_current_player
from ..models import CurrentPlayer
from ..schemas.settings import WarModeRequest, WarModeResponse

router = APIRouter()


@router.get("/war-mode")
def get_war_mode(player: CurrentPlayer = Depends(get_current_player)) -> WarModeResponse:
    active = db.get_setting(player.player_id, "war_mode_active", "0") == "1"
    started_raw = db.get_setting(player.player_id, "war_mode_started_at")
    return WarModeResponse(active=active, started_at=int(started_raw) if started_raw else None)


@router.put("/war-mode")
def set_war_mode(body: WarModeRequest, player: CurrentPlayer = Depends(get_current_player)) -> WarModeResponse:
    current = db.get_setting(player.player_id, "war_mode_active", "0") == "1"
    db.set_setting(player.player_id, "war_mode_active", "1" if body.active else "0")
    # Only re-stamp the start time on a false -> true transition, matching the old
    # Streamlit page's guard (`if new_state != war_mode_active: ... if new_state: stamp`) —
    # flipping it on when it's already on is a no-op that leaves the original start time.
    if body.active and not current:
        db.set_setting(player.player_id, "war_mode_started_at", str(int(time.time())))
    started_raw = db.get_setting(player.player_id, "war_mode_started_at")
    return WarModeResponse(active=body.active, started_at=int(started_raw) if started_raw else None)
