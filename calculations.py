import datetime

import pandas as pd

IGNORED_CATEGORY = "Ignored"

CATEGORY_KEYWORDS = {
    "Ranked War": ["attack", "war", "chain", "hospitaliz"],
    "Flying": ["travel", "abroad", "item market", "trading", "flight", "airstrip"],
    "Crimes & OCs": ["crime", "organized crime", "organised crime"],
    "Gym & Happy Jumps": ["gym", "happy", "train", "workout"],
    "Job": ["company", "job ", "employee", "work"],
    "Stock Market": ["stock", "share", "acquisition"],
    "Transfer": ["sent you", "gave you", "you sent", "you gave", "transfer"],
    "Gift": ["gift"],
    "Casino": ["casino", "slot", "roulette", "blackjack", "poker", "spin the wheel"],
}


def auto_categorize(title: str | None, category: str | None, war_mode_active: bool) -> str:
    text = f"{title or ''} {category or ''}".lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if cat == "Ranked War" and not war_mode_active:
            continue
        if any(keyword in text for keyword in keywords):
            return cat
    return "Uncategorized"


NETWORTH_BREAKDOWN_FIELDS = [
    ("Networth Total", "networth"),
    ("Pending", "nw_pending"),
    ("Wallet", "nw_wallet"),
    ("Bank", "nw_bank"),
    ("Points @ $", "nw_points"),
    ("Cayman", "nw_cayman"),
    ("Vault", "nw_vault"),
    ("Piggy Bank", "nw_piggybank"),
    ("Items", "nw_items"),
    ("Display Case", "nw_displaycase"),
    ("Bazaar", "nw_bazaar"),
    ("Trade", None),
    ("Items Market", "nw_itemmarket"),
    ("Properties", "nw_properties"),
    ("Stock Market", "nw_stockmarket"),
    ("Auction House", "nw_auctionhouse"),
    ("Company", "nw_company"),
    ("Bookie", "nw_bookie"),
    ("Enlisted Cars", "nw_enlistedcars"),
    ("Loan", "nw_loan"),
    ("Unpaid Fees", "nw_unpaidfees"),
]


def networth_breakdown(snapshot) -> pd.DataFrame:
    rows = []
    for label, column in NETWORTH_BREAKDOWN_FIELDS:
        if column is None:
            rows.append({"component": label, "amount": None})
        else:
            rows.append({"component": label, "amount": snapshot[column]})
    return pd.DataFrame(rows)


def _num(value) -> int:
    return value or 0


def liquid_total(snapshot) -> int:
    return _num(snapshot["money_onhand"]) + _num(snapshot["vault_amount"]) + _num(snapshot["bank_amount"])


def total_cashflow(snapshots: list) -> int:
    if len(snapshots) < 2:
        return 0
    return liquid_total(snapshots[-1]) - liquid_total(snapshots[0])


def elapsed_days(snapshots: list) -> float:
    if len(snapshots) < 2:
        return 0.0
    seconds = snapshots[-1]["synced_at"] - snapshots[0]["synced_at"]
    return seconds / 86400


def cashflow_per_day(snapshots: list) -> float:
    days = elapsed_days(snapshots)
    if days <= 0:
        return 0.0
    return total_cashflow(snapshots) / days


def build_deltas_dataframe(snapshots: list) -> pd.DataFrame:
    rows = []
    for prev, curr in zip(snapshots, snapshots[1:]):
        rows.append(
            {
                "from_ts": prev["synced_at"],
                "to_ts": curr["synced_at"],
                "to_date": datetime.datetime.utcfromtimestamp(curr["synced_at"]).date(),
                "cashflow_delta": liquid_total(curr) - liquid_total(prev),
                "networth": curr["networth"],
            }
        )
    return pd.DataFrame(rows)


def daily_series(snapshots: list) -> pd.DataFrame:
    df = build_deltas_dataframe(snapshots)
    if df.empty:
        return df
    daily = df.groupby("to_date").agg(
        cashflow_delta=("cashflow_delta", "sum"),
        networth=("networth", "last"),
    ).reset_index()
    return daily


def category_breakdown(log_entries: list, cashflow_total: int, categories: list[str]) -> pd.DataFrame:
    totals: dict[str, float] = {cat: 0.0 for cat in [*categories, "Uncategorized"]}
    for entry in log_entries:
        amount = entry["amount"]
        if amount is None:
            continue
        cat = entry["app_category"] or "Uncategorized"
        if cat == IGNORED_CATEGORY:
            continue
        totals[cat] = totals.get(cat, 0.0) + amount
    attributed = sum(totals.values())
    totals["Unattributed"] = cashflow_total - attributed
    df = pd.DataFrame([{"category": cat, "amount": amt} for cat, amt in totals.items() if amt != 0])
    return df


def _to_date(ts: int) -> datetime.date:
    return datetime.datetime.utcfromtimestamp(ts).date()


def _iso_week(ts: int) -> tuple:
    dt = datetime.datetime.utcfromtimestamp(ts)
    iso = dt.isocalendar()
    return (iso[0], iso[1])


def task_needs_reset(task, now_ts: int, war_mode_started_at: int | None) -> bool:
    if not task["is_done_current_cycle"]:
        return False
    last = task["last_completed_at"]
    if last is None:
        return False
    repeat_type = task["repeat_type"]
    if repeat_type == "once":
        return False
    if repeat_type == "daily":
        return _to_date(last) < _to_date(now_ts)
    if repeat_type == "weekly":
        return _iso_week(last) < _iso_week(now_ts)
    if repeat_type == "every_x_days":
        interval = task["repeat_interval_days"] or 1
        return now_ts >= last + interval * 86400
    if repeat_type == "war_day":
        if war_mode_started_at is None:
            return False
        return last < war_mode_started_at
    return False


REPEAT_TYPE_LABELS = {
    "daily": "Daily",
    "weekly": "Weekly",
    "every_x_days": "Every X Days",
    "once": "One-off",
    "war_day": "On War Days",
}
