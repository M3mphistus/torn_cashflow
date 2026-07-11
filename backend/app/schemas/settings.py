from .common import CamelModel


class WarModeResponse(CamelModel):
    active: bool
    started_at: int | None


class WarModeRequest(CamelModel):
    active: bool
