from . import db, torn_api
from .errors import ApiError


def login_error(exc: Exception) -> ApiError:
    """Map a Torn error raised while validating a freshly pasted key at login.
    Any TornAPIError here means the key itself didn't work for this purpose."""
    if isinstance(exc, torn_api.TornAPIError):
        return ApiError(401, str(exc), "invalid_api_key", torn_error_code=exc.code)
    return ApiError(502, str(exc), "torn_network_error")


def general_error(player_id: int, exc: Exception) -> ApiError:
    """Map a Torn error raised while using an already-stored key. Only code 2
    ("Incorrect API key") means the stored key itself is bad — everything else
    (rate limit, maintenance, temporary backend error, network failure) is
    transient and must not mark the key invalid."""
    if isinstance(exc, torn_api.TornAPIError):
        if exc.code == 2:
            db.invalidate_player_key(player_id)
            return ApiError(401, str(exc), "invalid_api_key", torn_error_code=exc.code)
        return ApiError(502, str(exc), "torn_api_error", torn_error_code=exc.code)
    return ApiError(502, str(exc), "torn_network_error")
