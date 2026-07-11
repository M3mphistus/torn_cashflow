from fastapi import APIRouter, Depends, Response

from .. import db, licensing, torn_api, torn_errors
from ..deps import get_current_player
from ..errors import ApiError
from ..models import CurrentPlayer
from ..schemas.auth import premium_status_to_dto
from ..schemas.licensing import (
    FactionPreviewResponse,
    GroupScanResponse,
    LicensingStatusResponse,
    ScanPaymentRequest,
    ScanPaymentResponse,
    TrialResponse,
)

router = APIRouter()


@router.get("/status")
def licensing_status(player: CurrentPlayer = Depends(get_current_player)) -> LicensingStatusResponse:
    status = licensing.get_premium_status(player)
    player_row = db.get_player(player.player_id)
    trial_used = bool(player_row and player_row["trial_used_at"] is not None)
    dto = premium_status_to_dto(status)
    return LicensingStatusResponse(**dto.model_dump(), trial_used=trial_used)


@router.post("/trial")
def start_trial(player: CurrentPlayer = Depends(get_current_player)) -> TrialResponse:
    result = licensing.start_free_trial(player)
    return TrialResponse(started=result.started, reason=result.reason, premium_until=result.premium_until)


@router.post("/scan-payment")
def scan_payment(
    body: ScanPaymentRequest, player: CurrentPlayer = Depends(get_current_player)
) -> ScanPaymentResponse:
    try:
        result = licensing.scan_and_activate_payment(player, lookback_days=body.lookback_days or 7)
    except (torn_api.TornAPIError, torn_api.TornNetworkError) as exc:
        raise torn_errors.general_error(player.player_id, exc) from exc
    return ScanPaymentResponse(
        credited_count=result.credited_count,
        weeks_added=result.weeks_added,
        new_premium_until=result.new_premium_until,
        already_credited_count=result.already_credited_count,
    )


@router.get("/faction-preview")
def faction_preview(player: CurrentPlayer = Depends(get_current_player)):
    if not player.faction_id:
        return Response(status_code=204)
    try:
        preview = licensing.get_faction_requirement_preview(player)
    except (torn_api.TornAPIError, torn_api.TornNetworkError) as exc:
        raise torn_errors.general_error(player.player_id, exc) from exc
    if preview is None:
        raise ApiError(502, "Could not read your faction's member list right now.", "faction_data_unavailable")
    return FactionPreviewResponse(
        member_count=preview.member_count,
        lifetime_covered_count=preview.lifetime_covered_count,
        payable_members=preview.payable_members,
        discount_pct=preview.discount_pct,
        required=preview.required,
    )


@router.post("/scan-group-payment")
def scan_group_payment(
    body: ScanPaymentRequest, player: CurrentPlayer = Depends(get_current_player)
) -> GroupScanResponse:
    try:
        result = licensing.scan_and_activate_group_payment(player, lookback_days=body.lookback_days or 7)
    except (torn_api.TornAPIError, torn_api.TornNetworkError) as exc:
        raise torn_errors.general_error(player.player_id, exc) from exc
    return GroupScanResponse(activated=result.activated, message=result.message, required=result.required, sent=result.sent)
