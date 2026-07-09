import math
import time
from dataclasses import dataclass

import streamlit as st

import auth
import db
import torn_api

BASE_XANAX_PER_PLAYER = 1
PREMIUM_PERIOD_DAYS = 28
TRIAL_PERIOD_DAYS = 7
WEEKS_PER_XANAX = PREMIUM_PERIOD_DAYS // 7
LIFETIME_SENTINEL_TS = 4102444800  # 2100-01-01 UTC — "forever" for this app's purposes

GROUP_DISCOUNT_TIERS = [
    (1, 0.00),
    (10, 0.10),
    (25, 0.20),
    (50, 0.30),
    (100, 0.40),
]


@dataclass
class PremiumStatus:
    is_premium: bool
    premium_until: int | None
    source: str  # 'none' | 'trial' | 'individual' | 'faction' | 'lifetime_individual' | 'lifetime_faction'


@dataclass
class FactionRequirementPreview:
    member_count: int
    lifetime_covered_count: int
    payable_members: int
    discount_pct: float
    required: int


@dataclass
class TrialResult:
    started: bool
    reason: str | None = None
    premium_until: int | None = None


@dataclass
class ScanResult:
    credited_count: int
    weeks_added: int
    new_premium_until: int | None
    already_credited_count: int


@dataclass
class GroupScanResult:
    activated: bool
    message: str
    required: int | None = None
    sent: int | None = None


def _dev_torn_player_id() -> int:
    return int(st.secrets["DEV_TORN_PLAYER_ID"])


def _xanax_item_id() -> int:
    return int(st.secrets["XANAX_ITEM_ID"])


def dev_profile_link() -> str:
    player_id = _dev_torn_player_id()
    name = st.secrets.get("DEV_TORN_PLAYER_NAME", "the developer")
    return f"[{name} [{player_id}]](https://www.torn.com/profiles.php?XID={player_id})"


def is_admin(player: auth.CurrentPlayer) -> bool:
    return player.player_id == _dev_torn_player_id()


def grant_lifetime(scope: str, key: int) -> None:
    db.upsert_license(scope, key, LIFETIME_SENTINEL_TS, origin="lifetime", last_payment_torn_log_id=None)


def revoke_lifetime(scope: str, key: int) -> bool:
    return db.revoke_license(scope, key)


def list_lifetime_grants() -> list[dict]:
    return db.list_lifetime_grants()


def get_premium_status(player: auth.CurrentPlayer) -> PremiumStatus:
    now_ts = int(time.time())
    best_until = 0
    best_source = "none"

    individual = db.get_license("individual", player.player_id)
    if individual and individual["premium_until"] > best_until:
        best_until = individual["premium_until"]
        if individual["origin"] == "trial":
            best_source = "trial"
        elif individual["origin"] == "lifetime":
            best_source = "lifetime_individual"
        else:
            best_source = "individual"

    if player.faction_id:
        faction = db.get_license("faction", player.faction_id)
        if faction and faction["premium_until"] > best_until:
            best_until = faction["premium_until"]
            best_source = "lifetime_faction" if faction["origin"] == "lifetime" else "faction"

    is_premium = best_until > now_ts
    return PremiumStatus(
        is_premium=is_premium,
        premium_until=best_until if best_until else None,
        source=best_source if is_premium else "none",
    )


def start_free_trial(player: auth.CurrentPlayer) -> TrialResult:
    player_row = db.get_player(player.player_id)
    if player_row and player_row["trial_used_at"] is not None:
        return TrialResult(started=False, reason="Trial already used.")

    now_ts = int(time.time())
    existing = db.get_license("individual", player.player_id)
    existing_until = existing["premium_until"] if existing else 0
    new_until = max(existing_until, now_ts) + TRIAL_PERIOD_DAYS * 86400

    db.upsert_license("individual", player.player_id, new_until, origin="trial", last_payment_torn_log_id=None)
    db.mark_trial_used(player.player_id, now_ts)

    return TrialResult(started=True, premium_until=new_until)


def _qualifying_entries(player: auth.CurrentPlayer, lookback_days: int) -> tuple[list[dict], set[str]]:
    now_ts = int(time.time())
    entries = torn_api.get_item_send_log_entries(player.api_key, now_ts - lookback_days * 86400, now_ts)
    already_credited = db.get_credited_payment_ids(player.player_id)
    dev_id = _dev_torn_player_id()
    qualifying = [
        e for e in entries
        if e["receiver"] == dev_id and e["torn_log_id"] not in already_credited
    ]
    return entries, qualifying, already_credited


def _xanax_qty(entry: dict) -> int:
    item_id = _xanax_item_id()
    return sum(i["qty"] or 0 for i in entry["items"] if i["id"] == item_id)


def scan_and_activate_payment(player: auth.CurrentPlayer, lookback_days: int = 7) -> ScanResult:
    now_ts = int(time.time())
    all_entries, qualifying, _ = _qualifying_entries(player, lookback_days)

    total_xanax = sum(_xanax_qty(e) for e in qualifying)
    if total_xanax <= 0:
        return ScanResult(credited_count=0, weeks_added=0, new_premium_until=None, already_credited_count=len(all_entries))

    for entry in qualifying:
        entry_xanax = _xanax_qty(entry)
        if entry_xanax <= 0:
            continue
        db.record_credited_payment(
            entry["torn_log_id"], player.player_id, "individual", None, entry_xanax * WEEKS_PER_XANAX
        )

    weeks_added = total_xanax * WEEKS_PER_XANAX
    existing = db.get_license("individual", player.player_id)
    existing_until = existing["premium_until"] if existing else 0
    new_until = max(existing_until, now_ts) + weeks_added * 7 * 86400

    latest_log_id = qualifying[-1]["torn_log_id"]
    db.upsert_license("individual", player.player_id, new_until, origin="payment", last_payment_torn_log_id=latest_log_id)

    return ScanResult(
        credited_count=len(qualifying),
        weeks_added=weeks_added,
        new_premium_until=new_until,
        already_credited_count=len(all_entries) - len(qualifying),
    )


def _group_discount_pct(member_count: int) -> float:
    discount = 0.0
    for min_count, tier_discount in GROUP_DISCOUNT_TIERS:
        if member_count >= min_count:
            discount = tier_discount
    return discount


def compute_group_requirement(member_count: int, lifetime_covered_count: int = 0) -> int:
    """Required bulk Xanax for a faction license.

    The discount tier is based on the FULL member count (a member who already
    has individual lifetime Premium still counts toward the faction's size/
    discount bracket), but the actual amount owed excludes members who are
    already covered — paying for them again would be redundant.
    """
    discount = _group_discount_pct(member_count)
    payable_members = max(0, member_count - lifetime_covered_count)
    return math.ceil(payable_members * (1 - discount))


def get_faction_requirement_preview(player: auth.CurrentPlayer) -> FactionRequirementPreview | None:
    if not player.faction_id:
        return None
    member_ids = torn_api.get_faction_member_ids(player.api_key, player.faction_id)
    if member_ids is None:
        return None
    lifetime_covered_count = db.count_lifetime_individual(member_ids)
    member_count = len(member_ids)
    discount_pct = _group_discount_pct(member_count)
    required = compute_group_requirement(member_count, lifetime_covered_count)
    return FactionRequirementPreview(
        member_count=member_count,
        lifetime_covered_count=lifetime_covered_count,
        payable_members=max(0, member_count - lifetime_covered_count),
        discount_pct=discount_pct,
        required=required,
    )


def scan_and_activate_group_payment(player: auth.CurrentPlayer, lookback_days: int = 7) -> GroupScanResult:
    if not player.faction_id:
        return GroupScanResult(activated=False, message="You're not in a faction.")

    member_ids = torn_api.get_faction_member_ids(player.api_key, player.faction_id)
    if member_ids is None:
        return GroupScanResult(activated=False, message="Could not read your faction's member count.")

    member_count = len(member_ids)
    lifetime_covered_count = db.count_lifetime_individual(member_ids)
    required = compute_group_requirement(member_count, lifetime_covered_count)

    now_ts = int(time.time())
    _, qualifying, _ = _qualifying_entries(player, lookback_days)
    total_xanax = sum(_xanax_qty(e) for e in qualifying)

    if total_xanax < required:
        return GroupScanResult(
            activated=False,
            message=f"Sent {total_xanax}, need {required} for your faction's {member_count} members.",
            required=required,
            sent=total_xanax,
        )

    for entry in qualifying:
        entry_xanax = _xanax_qty(entry)
        if entry_xanax <= 0:
            continue
        db.record_credited_payment(entry["torn_log_id"], player.player_id, "faction", player.faction_id, entry_xanax)

    existing = db.get_license("faction", player.faction_id)
    existing_until = existing["premium_until"] if existing else 0
    new_until = max(existing_until, now_ts) + PREMIUM_PERIOD_DAYS * 86400

    latest_log_id = qualifying[-1]["torn_log_id"]
    db.upsert_license("faction", player.faction_id, new_until, origin="payment", last_payment_torn_log_id=latest_log_id)

    return GroupScanResult(
        activated=True,
        message=f"Faction license activated for {member_count} members ({total_xanax} Xanax sent, {required} required).",
        required=required,
        sent=total_xanax,
    )


def require_premium(feature_name: str, player: auth.CurrentPlayer) -> bool:
    status = get_premium_status(player)
    if status.is_premium:
        return True
    st.warning(f"**{feature_name}** is a Premium feature.")
    st.write(
        f"Send **1 Xanax** to {dev_profile_link()} for 4 weeks of Premium — "
        "or check your free trial / faction options on the **Settings** page."
    )
    return False
