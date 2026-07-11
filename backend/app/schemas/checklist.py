from .common import CamelModel


class ChecklistTaskDTO(CamelModel):
    id: int
    title: str
    description: str | None
    repeat_type: str
    repeat_interval_days: int | None
    created_at: int
    last_completed_at: int | None
    is_done_current_cycle: bool


def checklist_task_to_dto(row: dict) -> ChecklistTaskDTO:
    return ChecklistTaskDTO(**row)


class ChecklistListResponse(CamelModel):
    tasks: list[ChecklistTaskDTO]


class ChecklistTaskResponse(CamelModel):
    task: ChecklistTaskDTO


class ChecklistTaskRequest(CamelModel):
    title: str
    description: str | None = None
    repeat_type: str
    repeat_interval_days: int | None = None


class SetDoneRequest(CamelModel):
    done: bool
