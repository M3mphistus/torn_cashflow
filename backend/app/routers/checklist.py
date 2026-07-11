import time

from fastapi import APIRouter, Depends

from .. import calculations, db, licensing
from ..deps import get_current_player
from ..errors import ApiError
from ..models import CurrentPlayer
from ..schemas.checklist import (
    ChecklistListResponse,
    ChecklistTaskRequest,
    ChecklistTaskResponse,
    SetDoneRequest,
    checklist_task_to_dto,
)

router = APIRouter()

VALID_REPEAT_TYPES = {"daily", "weekly", "every_x_days", "once", "war_day"}


def _validate_body(body: ChecklistTaskRequest) -> None:
    if body.repeat_type not in VALID_REPEAT_TYPES:
        raise ApiError(400, "Invalid repeatType.", "invalid_request")
    if body.repeat_type == "every_x_days" and (not body.repeat_interval_days or body.repeat_interval_days < 1):
        raise ApiError(400, "repeatIntervalDays is required and must be >= 1 for every_x_days.", "invalid_request")
    if body.repeat_type != "every_x_days":
        body.repeat_interval_days = None


@router.get("")
def list_checklist(player: CurrentPlayer = Depends(get_current_player)) -> ChecklistListResponse:
    now_ts = int(time.time())
    premium_status = licensing.get_premium_status(player)
    if premium_status.is_premium:
        started_raw = db.get_setting(player.player_id, "war_mode_started_at")
        war_mode_started_at = int(started_raw) if started_raw else None
        for task in db.list_checklist_tasks(player.player_id):
            if calculations.task_needs_reset(task, now_ts, war_mode_started_at):
                db.reset_task_cycle(player.player_id, task["id"])
    tasks = db.list_checklist_tasks(player.player_id)
    return ChecklistListResponse(tasks=[checklist_task_to_dto(t) for t in tasks])


@router.post("", status_code=201)
def create_checklist(
    body: ChecklistTaskRequest, player: CurrentPlayer = Depends(get_current_player)
) -> ChecklistTaskResponse:
    _validate_body(body)
    task_id = db.create_checklist_task(
        player.player_id, body.title, body.description or "", body.repeat_type, body.repeat_interval_days
    )
    task = db.get_checklist_task_by_id(player.player_id, task_id)
    return ChecklistTaskResponse(task=checklist_task_to_dto(task))


@router.patch("/{task_id}")
def update_checklist(
    task_id: int, body: ChecklistTaskRequest, player: CurrentPlayer = Depends(get_current_player)
) -> ChecklistTaskResponse:
    _validate_body(body)
    db.update_checklist_task(
        player.player_id, task_id, body.title, body.description or "", body.repeat_type, body.repeat_interval_days
    )
    task = db.get_checklist_task_by_id(player.player_id, task_id)
    if task is None:
        raise ApiError(404, "Checklist task not found.", "not_found")
    return ChecklistTaskResponse(task=checklist_task_to_dto(task))


@router.delete("/{task_id}", status_code=204)
def delete_checklist(task_id: int, player: CurrentPlayer = Depends(get_current_player)) -> None:
    db.delete_checklist_task(player.player_id, task_id)


@router.post("/{task_id}/done")
def set_done(
    task_id: int, body: SetDoneRequest, player: CurrentPlayer = Depends(get_current_player)
) -> ChecklistTaskResponse:
    task = db.get_checklist_task_by_id(player.player_id, task_id)
    if task is None:
        raise ApiError(404, "Checklist task not found.", "not_found")
    completed_at = int(time.time()) if body.done else task["last_completed_at"]
    db.set_task_done(player.player_id, task_id, body.done, completed_at)
    task = db.get_checklist_task_by_id(player.player_id, task_id)
    return ChecklistTaskResponse(task=checklist_task_to_dto(task))
