import pandas as pd
from fastapi import APIRouter, Depends, Query

from .. import calculations, db
from ..deps import get_current_player
from ..models import CurrentPlayer
from ..schemas.dashboard import (
    CategoryAmountDTO,
    DailyCashflowDTO,
    DailyNetworthDTO,
    DashboardBoundsResponse,
    DashboardResponse,
    NetworthComponentDTO,
)
from ..schemas.snapshots import snapshot_to_dto

router = APIRouter()


@router.get("/bounds")
def get_dashboard_bounds(player: CurrentPlayer = Depends(get_current_player)) -> DashboardBoundsResponse:
    """The full min/max timestamp span available to this player — snapshots AND log entries.

    A snapshot only marks a sync moment; a Full History Sync pulls log entries reaching back
    far further than any snapshot's own history. Bounding the Dashboard's presets by snapshot
    timestamps alone silently clips "All time" (and every relative preset) to exclude real,
    older cashflow data that's actually in the database.
    """
    snapshot_range = db.get_snapshot_timestamp_range(player.player_id)
    entry_range = db.get_log_entry_timestamp_range(player.player_id)
    if snapshot_range is None and entry_range is None:
        return DashboardBoundsResponse(min_ts=None, max_ts=None)
    candidates = [r for r in (snapshot_range, entry_range) if r is not None]
    min_ts = min(r[0] for r in candidates)
    max_ts = max(r[1] for r in candidates)
    return DashboardBoundsResponse(min_ts=min_ts, max_ts=max_ts)


@router.get("")
def get_dashboard(
    start_ts: int = Query(..., alias="startTs"),
    end_ts: int = Query(..., alias="endTs"),
    player: CurrentPlayer = Depends(get_current_player),
) -> DashboardResponse:
    snapshots = db.get_snapshots(player.player_id, start_ts, end_ts)
    log_entries = db.get_log_entries(player.player_id, start_ts, end_ts)
    categories = db.list_categories(player.player_id)

    cashflow_total = calculations.cashflow_from_entries(log_entries)
    cashflow_per_day = calculations.cashflow_per_day_from_entries(log_entries, start_ts, end_ts)

    breakdown_df = calculations.category_breakdown(log_entries, categories)
    category_breakdown = [
        CategoryAmountDTO(category=row["category"], amount=row["amount"])
        for row in breakdown_df.to_dict("records")
    ]

    if snapshots:
        nw_df = calculations.networth_breakdown(snapshots[-1])
        networth_breakdown = [
            NetworthComponentDTO(
                component=row["component"], amount=row["amount"] if pd.notna(row["amount"]) else None
            )
            for row in nw_df.to_dict("records")
        ]
    else:
        networth_breakdown = [
            NetworthComponentDTO(component=label, amount=None) for label, _ in calculations.NETWORTH_BREAKDOWN_FIELDS
        ]

    daily_cf_df = calculations.daily_cashflow_from_entries(log_entries)
    daily_cashflow = [
        DailyCashflowDTO(date=row["to_date"].isoformat(), cashflow_delta=row["cashflow_delta"])
        for row in daily_cf_df.to_dict("records")
    ]

    daily_nw_df = calculations.daily_networth_from_snapshots(snapshots)
    daily_networth = [
        DailyNetworthDTO(date=row["to_date"].isoformat(), networth=row["networth"])
        for row in daily_nw_df.to_dict("records")
    ]

    return DashboardResponse(
        cashflow_total=cashflow_total,
        cashflow_per_day=cashflow_per_day,
        category_breakdown=category_breakdown,
        networth_breakdown=networth_breakdown,
        daily_cashflow=daily_cashflow,
        daily_networth=daily_networth,
        snapshots=[snapshot_to_dto(s) for s in snapshots],
    )
