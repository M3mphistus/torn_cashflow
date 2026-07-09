import time

import requests

BASE_URL = "https://api.torn.com"
REQUEST_TIMEOUT_SECONDS = 15
FULL_LOG_MAX_PAGES = 200
FULL_LOG_REQUEST_DELAY_SECONDS = 0.7

ERROR_MESSAGES = {
    0: "Unknown Torn API error.",
    1: "API key is empty. Add your Full Access key in Settings.",
    2: "Incorrect API key. Check the key in Settings.",
    3: "Unknown request type.",
    4: "Requested field(s) are not available for this selection.",
    5: "Rate limit reached (100 requests/minute). Wait a bit and try again.",
    6: "Incorrect ID provided.",
    7: "No relation between the ID and the selection.",
    8: "Current IP is banned for a small period.",
    9: "API is currently disabled for maintenance.",
    10: "Key owner is in federal jail and the API is disabled for them.",
    11: "Too many key changes, please wait before trying again.",
    12: "Key read error, please try again.",
    13: "Key is temporarily disabled due to inactivity.",
    14: "Daily read limit reached for this key.",
    15: "Temporary Torn API error, please try again.",
    16: "This key's access level is not high enough for this request (needs Full Access).",
    17: "Backend error occurred, please try again.",
    18: "API key is paused by its owner.",
    19: "Access must be migrated, please check Torn's API documentation.",
    20: "Rate limit exceeded for this endpoint.",
}


class TornAPIError(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class TornNetworkError(Exception):
    pass


def _request(selections: str, api_key: str, extra_params: dict | None = None) -> dict:
    if not api_key:
        raise TornAPIError(ERROR_MESSAGES[1], code=1)

    params = {"selections": selections, "key": api_key}
    if extra_params:
        params.update(extra_params)

    try:
        response = requests.get(f"{BASE_URL}/user/", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise TornNetworkError("Torn API request timed out.")
    except requests.exceptions.RequestException:
        raise TornNetworkError("Could not reach the Torn API. Check your internet connection.")

    try:
        data = response.json()
    except ValueError:
        raise TornNetworkError("Torn API returned an unreadable response.")

    if isinstance(data, dict) and "error" in data:
        code = data["error"].get("code")
        message = ERROR_MESSAGES.get(code, data["error"].get("error", "Unknown Torn API error."))
        raise TornAPIError(message, code=code)

    return data


def get_bars(api_key: str) -> dict:
    data = _request("bars", api_key)
    return {
        "energy_current": _safe_int(data.get("energy", {}).get("current")),
        "energy_maximum": _safe_int(data.get("energy", {}).get("maximum")),
        "nerve_current": _safe_int(data.get("nerve", {}).get("current")),
        "nerve_maximum": _safe_int(data.get("nerve", {}).get("maximum")),
        "happy_current": _safe_int(data.get("happy", {}).get("current")),
        "happy_maximum": _safe_int(data.get("happy", {}).get("maximum")),
    }


def get_money(api_key: str) -> dict:
    data = _request("money", api_key)
    return {
        "money_onhand": _safe_int(data.get("money_onhand")),
        "money_points": _safe_int(data.get("points")),
        "vault_amount": _safe_int(data.get("city_bank", {}).get("amount") if isinstance(data.get("city_bank"), dict) else data.get("vault_amount")),
        "bank_amount": _safe_int(data.get("bank", {}).get("amount") if isinstance(data.get("bank"), dict) else data.get("bank_amount")),
    }


NETWORTH_STAT_FIELDS = {
    "nw_pending": "networthpending",
    "nw_wallet": "networthwallet",
    "nw_bank": "networthbank",
    "nw_points": "networthpoints",
    "nw_cayman": "networthcayman",
    "nw_vault": "networthvault",
    "nw_piggybank": "networthpiggybank",
    "nw_items": "networthitems",
    "nw_displaycase": "networthdisplaycase",
    "nw_bazaar": "networthbazaar",
    "nw_itemmarket": "networthitemmarket",
    "nw_properties": "networthproperties",
    "nw_stockmarket": "networthstockmarket",
    "nw_auctionhouse": "networthauctionhouse",
    "nw_company": "networthcompany",
    "nw_bookie": "networthbookie",
    "nw_enlistedcars": "networthenlistedcars",
    "nw_loan": "networthloan",
    "nw_unpaidfees": "networthunpaidfees",
}

PERSONALSTATS_FIELDS = ",".join(
    ["networth", "refills", "nerverefills", "energydrinkused", "xantaken", *NETWORTH_STAT_FIELDS.values()]
)


def get_personalstats(api_key: str) -> dict:
    data = _request("personalstats", api_key, {"stat": PERSONALSTATS_FIELDS})
    stats = data.get("personalstats", data)
    result = {
        "networth": _safe_int(stats.get("networth")),
        "refills_total": _safe_int(stats.get("refills")),
        "nerverefills_total": _safe_int(stats.get("nerverefills")),
        "energydrinkused_total": _safe_int(stats.get("energydrinkused")),
        "xantaken_total": _safe_int(stats.get("xantaken")),
    }
    for column, stat_name in NETWORTH_STAT_FIELDS.items():
        result[column] = _safe_int(stats.get(stat_name))
    return result


AMOUNT_KEYS = ("money", "amount", "cost_total", "cost", "cash", "worth", "value", "money_gained", "money_lost")

TITLE_AMOUNT_OVERRIDES = {
    "Stock buy": ("worth", -1),
    "Stock sell": ("worth", 1),
}


def _extract_amount(title: str | None, details: dict) -> float | None:
    override = TITLE_AMOUNT_OVERRIDES.get(title)
    if override:
        field_name, sign = override
        value = details.get(field_name)
        if value in (None, ""):
            return None
        try:
            return sign * abs(float(value))
        except (TypeError, ValueError):
            return None

    for key in AMOUNT_KEYS:
        if key in details and details[key] not in (None, ""):
            try:
                return float(details[key])
            except (TypeError, ValueError):
                return None
    return None


def get_log(api_key: str, from_ts: int, to_ts: int) -> list[dict]:
    params = {"from": from_ts, "to": to_ts}
    data = _request("log", api_key, params)
    log_data = data.get("log", {})

    if isinstance(log_data, dict):
        items = log_data.items()
    elif isinstance(log_data, list):
        items = enumerate(log_data)
    else:
        items = []

    entries = []
    for log_id, entry in items:
        if not isinstance(entry, dict):
            continue
        details = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        title = entry.get("title") or entry.get("log_name")
        amount = _extract_amount(title, details)
        entries.append(
            {
                "torn_log_id": str(entry.get("id", log_id)),
                "timestamp": _safe_int(entry.get("timestamp")),
                "category": entry.get("category") or entry.get("log"),
                "title": title,
                "raw_text": entry.get("text") or entry.get("title"),
                "amount": amount,
            }
        )
    return entries


def get_full_log(api_key: str, progress_callback=None) -> list[dict]:
    all_entries = []
    seen_ids = set()
    to_ts = int(time.time())

    for page in range(FULL_LOG_MAX_PAGES):
        batch = get_log(api_key, 0, to_ts)
        if not batch:
            break

        new_entries = [e for e in batch if e["torn_log_id"] not in seen_ids]
        for e in new_entries:
            seen_ids.add(e["torn_log_id"])
        all_entries.extend(new_entries)

        timestamps = [e["timestamp"] for e in batch if e["timestamp"]]
        if not timestamps:
            break
        oldest_ts = min(timestamps)

        if progress_callback:
            progress_callback(len(all_entries), oldest_ts, page + 1)

        if not new_entries or oldest_ts >= to_ts:
            break
        to_ts = oldest_ts - 1

        time.sleep(FULL_LOG_REQUEST_DELAY_SECONDS)

    return all_entries


def get_basic_profile(api_key: str) -> dict:
    data = _request("profile", api_key)
    faction = data.get("faction") if isinstance(data.get("faction"), dict) else {}
    return {
        "player_id": _safe_int(data.get("player_id")),
        "name": data.get("name"),
        "faction_id": _safe_int(faction.get("faction_id")) or None,
    }


def get_faction_member_count(api_key: str, faction_id: int) -> int | None:
    data = _request_faction(faction_id, api_key)
    members = data.get("members")
    if not isinstance(members, dict):
        return None
    return len(members)


def _request_faction(faction_id: int, api_key: str) -> dict:
    params = {"selections": "basic", "key": api_key}
    try:
        response = requests.get(f"{BASE_URL}/faction/{faction_id}", params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise TornNetworkError("Torn API request timed out.")
    except requests.exceptions.RequestException:
        raise TornNetworkError("Could not reach the Torn API. Check your internet connection.")

    try:
        data = response.json()
    except ValueError:
        raise TornNetworkError("Torn API returned an unreadable response.")

    if isinstance(data, dict) and "error" in data:
        code = data["error"].get("code")
        message = ERROR_MESSAGES.get(code, data["error"].get("error", "Unknown Torn API error."))
        raise TornAPIError(message, code=code)

    return data


ITEM_SEND_TITLE = "Item send"


def get_item_send_log_entries(api_key: str, from_ts: int, to_ts: int) -> list[dict]:
    params = {"from": from_ts, "to": to_ts}
    data = _request("log", api_key, params)
    log_data = data.get("log", {})

    if isinstance(log_data, dict):
        items = log_data.items()
    elif isinstance(log_data, list):
        items = enumerate(log_data)
    else:
        items = []

    entries = []
    for log_id, entry in items:
        if not isinstance(entry, dict) or entry.get("title") != ITEM_SEND_TITLE:
            continue
        details = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        sent_items = details.get("items") if isinstance(details.get("items"), list) else []
        entries.append(
            {
                "torn_log_id": str(entry.get("id", log_id)),
                "timestamp": _safe_int(entry.get("timestamp")),
                "receiver": _safe_int(details.get("receiver")),
                "items": [
                    {"id": _safe_int(i.get("id")), "qty": _safe_int(i.get("qty"))}
                    for i in sent_items
                    if isinstance(i, dict)
                ],
            }
        )
    return entries


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
