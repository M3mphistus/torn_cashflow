from .common import CamelModel


class GrantDTO(CamelModel):
    scope: str
    key: int
    activated_at: int


class GrantListResponse(CamelModel):
    grants: list[GrantDTO]


class GrantRequest(CamelModel):
    scope: str
    key: int


def grant_row_to_dto(row: dict) -> GrantDTO:
    key = row["torn_player_id"] if row["scope"] == "individual" else row["group_id"]
    return GrantDTO(scope=row["scope"], key=key, activated_at=row["activated_at"])
