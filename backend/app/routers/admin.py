import time

from fastapi import APIRouter, Depends

from .. import licensing
from ..deps import require_admin
from ..models import CurrentPlayer
from ..schemas.admin import GrantDTO, GrantListResponse, GrantRequest, grant_row_to_dto

router = APIRouter()


@router.get("/lifetime-grants")
def list_grants(player: CurrentPlayer = Depends(require_admin)) -> GrantListResponse:
    grants = licensing.list_lifetime_grants()
    return GrantListResponse(grants=[grant_row_to_dto(g) for g in grants])


@router.post("/lifetime-grants", status_code=201)
def create_grant(body: GrantRequest, player: CurrentPlayer = Depends(require_admin)) -> GrantDTO:
    licensing.grant_lifetime(body.scope, body.key)
    return GrantDTO(scope=body.scope, key=body.key, activated_at=int(time.time()))


@router.delete("/lifetime-grants", status_code=204)
def delete_grant(body: GrantRequest, player: CurrentPlayer = Depends(require_admin)) -> None:
    licensing.revoke_lifetime(body.scope, body.key)
