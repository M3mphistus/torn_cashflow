from .common import CamelModel
from .snapshots import SnapshotDTO


class CategoryAmountDTO(CamelModel):
    category: str
    amount: float


class NetworthComponentDTO(CamelModel):
    component: str
    amount: float | None


class DailyCashflowDTO(CamelModel):
    date: str
    cashflow_delta: float


class DailyNetworthDTO(CamelModel):
    date: str
    networth: int | None


class DashboardResponse(CamelModel):
    cashflow_total: float
    cashflow_per_day: float
    category_breakdown: list[CategoryAmountDTO]
    networth_breakdown: list[NetworthComponentDTO]
    daily_cashflow: list[DailyCashflowDTO]
    daily_networth: list[DailyNetworthDTO]
    snapshots: list[SnapshotDTO]


class DashboardBoundsResponse(CamelModel):
    min_ts: int | None
    max_ts: int | None
