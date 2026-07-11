from fastapi import APIRouter, Depends, Query

from .. import db
from ..deps import get_current_player
from ..errors import ApiError
from ..models import CurrentPlayer
from ..schemas.snapshots import (
    NoteRequest,
    SnapshotListResponse,
    SnapshotOrNoneResponse,
    SnapshotSingleResponse,
    snapshot_to_dto,
)

router = APIRouter()


@router.get("")
def list_snapshots(
    start_ts: int | None = Query(default=None, alias="startTs"),
    end_ts: int | None = Query(default=None, alias="endTs"),
    player: CurrentPlayer = Depends(get_current_player),
) -> SnapshotListResponse:
    rows = db.get_snapshots(player.player_id, start_ts, end_ts)
    return SnapshotListResponse(snapshots=[snapshot_to_dto(r) for r in rows])


@router.get("/latest")
def latest_snapshot(player: CurrentPlayer = Depends(get_current_player)) -> SnapshotOrNoneResponse:
    row = db.get_latest_snapshot(player.player_id)
    return SnapshotOrNoneResponse(snapshot=snapshot_to_dto(row) if row else None)


@router.patch("/{snapshot_id}/note")
def update_note(
    snapshot_id: int, body: NoteRequest, player: CurrentPlayer = Depends(get_current_player)
) -> SnapshotSingleResponse:
    db.update_snapshot_note(player.player_id, snapshot_id, body.note)
    row = db.get_snapshot_by_id(player.player_id, snapshot_id)
    if row is None:
        raise ApiError(404, "Snapshot not found.", "not_found")
    return SnapshotSingleResponse(snapshot=snapshot_to_dto(row))
