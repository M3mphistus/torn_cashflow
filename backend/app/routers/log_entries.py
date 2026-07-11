from fastapi import APIRouter, Depends, Query

from .. import calculations, db
from ..deps import get_current_player
from ..errors import ApiError
from ..models import CurrentPlayer
from ..schemas.log_entries import (
    IgnoreLogEntryRequest,
    LogEntryListResponse,
    LogEntryMutationResponse,
    LogEntryPageResponse,
    LogEntrySingleResponse,
    RecategorizePeriodRequest,
    UpdateLogEntryRequest,
    UpdatedCountResponse,
    log_entry_to_dto,
)

router = APIRouter()

ENTRY_LIST_DISPLAY_LIMIT = 25


@router.get("")
def list_log_entries(
    start_ts: int | None = Query(default=None, alias="startTs"),
    end_ts: int | None = Query(default=None, alias="endTs"),
    category: str | None = Query(default=None),
    player: CurrentPlayer = Depends(get_current_player),
) -> LogEntryListResponse:
    rows = db.get_log_entries(player.player_id, start_ts, end_ts, category)
    return LogEntryListResponse(entries=[log_entry_to_dto(r) for r in rows])


@router.get("/uncategorized")
def uncategorized(
    limit: int = Query(default=ENTRY_LIST_DISPLAY_LIMIT), player: CurrentPlayer = Depends(get_current_player)
) -> LogEntryPageResponse:
    total = db.get_category_counts(player.player_id).get("Uncategorized", 0)
    rows = db.get_uncategorized_log_entries(player.player_id, limit=limit)
    return LogEntryPageResponse(entries=[log_entry_to_dto(r) for r in rows], total_count=total)


@router.get("/ignored")
def ignored(
    limit: int = Query(default=ENTRY_LIST_DISPLAY_LIMIT), player: CurrentPlayer = Depends(get_current_player)
) -> LogEntryPageResponse:
    total = db.get_category_counts(player.player_id).get(calculations.IGNORED_CATEGORY, 0)
    rows = db.get_entries_by_category(player.player_id, calculations.IGNORED_CATEGORY, limit=limit)
    return LogEntryPageResponse(entries=[log_entry_to_dto(r) for r in rows], total_count=total)


def _apply_category_and_bulk(
    player_id: int, entry_id: int, app_category: str, user_note: str | None
) -> LogEntryMutationResponse:
    db.update_log_entry_category(player_id, entry_id, app_category, user_note)
    entry = db.get_log_entry_by_id(player_id, entry_id)
    if entry is None:
        raise ApiError(404, "Log entry not found.", "not_found")
    bulk_updated = 0
    if entry["title"]:
        db.upsert_category_rule(player_id, entry["title"], app_category)
        bulk_updated = db.bulk_categorize_by_title(player_id, entry["title"], app_category, exclude_entry_id=entry_id)
    return LogEntryMutationResponse(entry=log_entry_to_dto(entry), bulk_updated_count=bulk_updated)


@router.patch("/{entry_id}")
def update_entry(
    entry_id: int, body: UpdateLogEntryRequest, player: CurrentPlayer = Depends(get_current_player)
) -> LogEntryMutationResponse:
    return _apply_category_and_bulk(player.player_id, entry_id, body.app_category, body.user_note)


@router.post("/{entry_id}/ignore")
def ignore_entry(
    entry_id: int, body: IgnoreLogEntryRequest, player: CurrentPlayer = Depends(get_current_player)
) -> LogEntryMutationResponse:
    return _apply_category_and_bulk(player.player_id, entry_id, calculations.IGNORED_CATEGORY, body.user_note)


@router.post("/{entry_id}/restore")
def restore_entry(entry_id: int, player: CurrentPlayer = Depends(get_current_player)) -> LogEntrySingleResponse:
    entry = db.get_log_entry_by_id(player.player_id, entry_id)
    if entry is None:
        raise ApiError(404, "Log entry not found.", "not_found")
    db.update_log_entry_category(player.player_id, entry_id, "Uncategorized", entry["user_note"])
    entry["app_category"] = "Uncategorized"
    return LogEntrySingleResponse(entry=log_entry_to_dto(entry))


@router.post("/recategorize-period")
def recategorize_period(
    body: RecategorizePeriodRequest, player: CurrentPlayer = Depends(get_current_player)
) -> UpdatedCountResponse:
    count = db.recategorize_period(player.player_id, body.start_ts, body.end_ts, body.app_category)
    return UpdatedCountResponse(updated_count=count)
