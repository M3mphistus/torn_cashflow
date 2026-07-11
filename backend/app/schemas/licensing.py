from .common import CamelModel


class LicensingStatusResponse(CamelModel):
    is_premium: bool
    premium_until: int | None
    is_lifetime: bool
    source: str
    is_expiring_soon: bool
    days_until_expiry: float | None
    trial_used: bool


class TrialResponse(CamelModel):
    started: bool
    reason: str | None
    premium_until: int | None


class ScanPaymentRequest(CamelModel):
    lookback_days: int | None = None


class ScanPaymentResponse(CamelModel):
    credited_count: int
    weeks_added: int
    new_premium_until: int | None
    already_credited_count: int


class FactionPreviewResponse(CamelModel):
    member_count: int
    lifetime_covered_count: int
    payable_members: int
    discount_pct: float
    required: int


class GroupScanResponse(CamelModel):
    activated: bool
    message: str
    required: int | None
    sent: int | None
