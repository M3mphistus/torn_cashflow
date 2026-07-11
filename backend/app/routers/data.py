from fastapi import APIRouter, Depends

from .. import db
from ..deps import get_current_player
from ..models import CurrentPlayer

router = APIRouter()


@router.delete("/data", status_code=204)
def delete_data(player: CurrentPlayer = Depends(get_current_player)) -> None:
    db.clear_synced_data(player.player_id)
