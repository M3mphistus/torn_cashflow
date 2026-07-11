import time

from fastapi import APIRouter, BackgroundTasks, Depends

from .. import calculations, db, licensing, torn_api, torn_errors
from ..deps import get_current_player, require_premium
from ..errors import ApiError
from ..models import CurrentPlayer
from ..schemas.snapshots import snapshot_to_dto
from ..schemas.sync import IncrementalSyncResponse, SyncJobResultDTO, SyncJobStartResponse, SyncJobStatusResponse

router = APIRouter()

AUTO_PAYMENT_CHECK_LOOKBACK_DAYS = 30  # wider than the manual button's 7, since syncing may not happen often


def _check_payments_after_sync(player: CurrentPlayer) -> str | None:
    messages = []
    individual = licensing.scan_and_activate_payment(player, lookback_days=AUTO_PAYMENT_CHECK_LOOKBACK_DAYS)
    if individual.credited_count > 0:
        messages.append(
            f"Credited {individual.weeks_added} week(s) of Premium from "
            f"{individual.credited_count} Xanax payment(s)."
        )
    if player.faction_id:
        group = licensing.scan_and_activate_group_payment(player, lookback_days=AUTO_PAYMENT_CHECK_LOOKBACK_DAYS)
        if group.activated:
            messages.append(group.message)
    return "  \n".join(messages) if messages else None


def _categorize_entries(player_id: int, entries: list[dict], war_mode_active: bool) -> list[dict]:
    rules = db.get_all_category_rules(player_id)
    prepared = []
    for entry in entries:
        title = entry.get("title")
        app_category = rules.get(title) if title else None
        if app_category is None:
            app_category = calculations.auto_categorize(title, entry.get("category"), war_mode_active)
        if app_category == "Uncategorized" and entry.get("amount") is None:
            app_category = calculations.IGNORED_CATEGORY
        prepared.append({**entry, "app_category": app_category})
    return prepared


@router.post("/incremental")
def sync_incremental(player: CurrentPlayer = Depends(get_current_player)) -> IncrementalSyncResponse:
    now_ts = int(time.time())
    last_sync_at = db.get_setting(player.player_id, "last_sync_at")
    from_ts = int(last_sync_at) if last_sync_at else now_ts - 7 * 86400
    war_mode_active = db.get_setting(player.player_id, "war_mode_active", "0") == "1"

    try:
        bars = torn_api.get_bars(player.api_key)
        money = torn_api.get_money(player.api_key)
        stats = torn_api.get_personalstats(player.api_key)
        log_entries = torn_api.get_log(player.api_key, from_ts, now_ts)
    except (torn_api.TornAPIError, torn_api.TornNetworkError) as exc:
        raise torn_errors.general_error(player.player_id, exc) from exc

    snapshot_fields = {"synced_at": now_ts, "war_mode_active": war_mode_active, **bars, **money, **stats}
    snapshot_id = db.insert_snapshot(player.player_id, snapshot_fields)
    prepared = _categorize_entries(player.player_id, log_entries, war_mode_active)
    db.insert_log_entries(player.player_id, snapshot_id, prepared)
    db.set_setting(player.player_id, "last_sync_at", str(now_ts))

    payment_message = _check_payments_after_sync(player)
    snapshot = db.get_latest_snapshot(player.player_id)
    return IncrementalSyncResponse(
        snapshot=snapshot_to_dto(snapshot),
        log_entries_stored=len(prepared),
        payment_message=payment_message,
    )


def _run_full_history_sync(
    job_id: int, player_id: int, api_key: str, snapshot_id: int, war_mode_active: bool
) -> None:
    try:
        all_entries: list[dict] = []
        seen_ids: set[str] = set()
        to_ts = int(time.time())
        for page in range(torn_api.FULL_LOG_MAX_PAGES):
            batch = torn_api.get_log(api_key, 0, to_ts)
            if not batch:
                break
            new_entries = [e for e in batch if e["torn_log_id"] not in seen_ids]
            seen_ids.update(e["torn_log_id"] for e in new_entries)
            all_entries.extend(new_entries)
            timestamps = [e["timestamp"] for e in batch if e["timestamp"]]
            if not timestamps:
                break
            oldest_ts = min(timestamps)
            db.update_sync_job_progress(job_id, page + 1, len(all_entries), oldest_ts)
            if not new_entries or oldest_ts >= to_ts:
                break
            to_ts = oldest_ts - 1
            time.sleep(torn_api.FULL_LOG_REQUEST_DELAY_SECONDS)

        existing_ids = db.get_existing_torn_log_ids(player_id)
        new_entries = [e for e in all_entries if e["torn_log_id"] not in existing_ids]
        already_stored = len(all_entries) - len(new_entries)
        prepared = _categorize_entries(player_id, new_entries, war_mode_active)
        db.insert_log_entries(player_id, snapshot_id, prepared)
        db.set_setting(player_id, "last_sync_at", str(int(time.time())))
        db.complete_sync_job(job_id, new_entries_stored=len(prepared), already_stored=already_stored)
    except torn_api.TornAPIError as exc:
        if exc.code == 2:
            db.invalidate_player_key(player_id)
        db.fail_sync_job(job_id, str(exc))
    except torn_api.TornNetworkError as exc:
        db.fail_sync_job(job_id, str(exc))
    except Exception as exc:  # last-resort guard so a stuck job always resolves (per spec: "on any exception")
        db.fail_sync_job(job_id, str(exc))


@router.post("/full-history", status_code=202)
def start_full_history_sync(
    background_tasks: BackgroundTasks, player: CurrentPlayer = Depends(require_premium)
) -> SyncJobStartResponse:
    now_ts = int(time.time())
    war_mode_active = db.get_setting(player.player_id, "war_mode_active", "0") == "1"
    try:
        bars = torn_api.get_bars(player.api_key)
        money = torn_api.get_money(player.api_key)
        stats = torn_api.get_personalstats(player.api_key)
    except (torn_api.TornAPIError, torn_api.TornNetworkError) as exc:
        raise torn_errors.general_error(player.player_id, exc) from exc

    snapshot_fields = {"synced_at": now_ts, "war_mode_active": war_mode_active, **bars, **money, **stats}
    snapshot_id = db.insert_snapshot(player.player_id, snapshot_fields)

    job_id = db.create_sync_job(player.player_id)
    background_tasks.add_task(
        _run_full_history_sync, job_id, player.player_id, player.api_key, snapshot_id, war_mode_active
    )
    return SyncJobStartResponse(job_id=job_id, status="running")


@router.get("/full-history/{job_id}")
def get_full_history_sync(job_id: int, player: CurrentPlayer = Depends(get_current_player)) -> SyncJobStatusResponse:
    job = db.get_sync_job(job_id)
    if job is None or job["torn_player_id"] != player.player_id:
        raise ApiError(404, "Sync job not found.", "not_found")

    result = None
    if job["status"] == "completed":
        result = SyncJobResultDTO(new_entries_stored=job["new_entries_stored"], already_stored=job["already_stored"])

    return SyncJobStatusResponse(
        job_id=job["id"],
        status=job["status"],
        pages_fetched=job["pages_fetched"],
        entries_fetched=job["entries_fetched"],
        oldest_timestamp=job["oldest_timestamp"],
        error=job["error"],
        result=result,
    )
