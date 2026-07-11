from .common import CamelModel


class LogEntryDTO(CamelModel):
    id: int
    torn_log_id: str | None
    timestamp: int
    category: str | None
    title: str | None
    raw_text: str | None
    amount: float | None
    app_category: str
    user_note: str | None


def log_entry_to_dto(row: dict) -> LogEntryDTO:
    return LogEntryDTO(**row)


class LogEntryListResponse(CamelModel):
    entries: list[LogEntryDTO]


class LogEntryPageResponse(CamelModel):
    entries: list[LogEntryDTO]
    total_count: int


class LogEntryMutationResponse(CamelModel):
    entry: LogEntryDTO
    bulk_updated_count: int


class LogEntrySingleResponse(CamelModel):
    entry: LogEntryDTO


class UpdateLogEntryRequest(CamelModel):
    app_category: str
    user_note: str | None = None


class IgnoreLogEntryRequest(CamelModel):
    user_note: str | None = None


class RecategorizePeriodRequest(CamelModel):
    start_ts: int
    end_ts: int
    app_category: str


class UpdatedCountResponse(CamelModel):
    updated_count: int
