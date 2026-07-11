from .. import licensing, security
from ..models import CurrentPlayer
from .common import CamelModel


class LoginRequest(CamelModel):
    api_key: str


class PlayerDTO(CamelModel):
    player_id: int
    name: str | None
    faction_id: int | None
    masked_api_key: str
    is_admin: bool


class PremiumStatusDTO(CamelModel):
    is_premium: bool
    premium_until: int | None
    is_lifetime: bool
    source: str
    is_expiring_soon: bool
    days_until_expiry: float | None


class PlayerSessionResponse(CamelModel):
    player: PlayerDTO
    premium: PremiumStatusDTO


_SOURCE_CAMEL = {
    "none": "none",
    "trial": "trial",
    "individual": "individual",
    "faction": "faction",
    "lifetime_individual": "lifetimeIndividual",
    "lifetime_faction": "lifetimeFaction",
}


def player_to_dto(player: CurrentPlayer) -> PlayerDTO:
    return PlayerDTO(
        player_id=player.player_id,
        name=player.name,
        faction_id=player.faction_id,
        masked_api_key=security.mask_key(player.api_key),
        is_admin=licensing.is_admin(player),
    )


def premium_status_to_dto(status: "licensing.PremiumStatus") -> PremiumStatusDTO:
    is_lifetime = status.premium_until is not None and status.premium_until >= licensing.LIFETIME_SENTINEL_TS
    return PremiumStatusDTO(
        is_premium=status.is_premium,
        premium_until=status.premium_until if status.is_premium else None,
        is_lifetime=is_lifetime,
        source=_SOURCE_CAMEL[status.source],
        is_expiring_soon=licensing.is_expiring_soon(status),
        days_until_expiry=licensing.days_until_expiry(status),
    )
