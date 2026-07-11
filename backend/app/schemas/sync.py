from .common import CamelModel
from .snapshots import SnapshotDTO


class IncrementalSyncResponse(CamelModel):
    snapshot: SnapshotDTO
    log_entries_stored: int
    payment_message: str | None


class SyncJobStartResponse(CamelModel):
    job_id: int
    status: str


class SyncJobResultDTO(CamelModel):
    new_entries_stored: int
    already_stored: int


class SyncJobStatusResponse(CamelModel):
    job_id: int
    status: str
    pages_fetched: int
    entries_fetched: int
    oldest_timestamp: int | None
    error: str | None
    result: SyncJobResultDTO | None
