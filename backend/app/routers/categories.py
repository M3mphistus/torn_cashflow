from fastapi import APIRouter, Depends, Query

from .. import calculations, db
from ..deps import get_current_player
from ..errors import ApiError
from ..models import CurrentPlayer
from ..schemas.categories import (
    CategoryDTO,
    CategoryListResponse,
    CategoryNameResponse,
    CreateCategoryRequest,
    ReassignCategoryRequest,
    TitleSummaryResponse,
    TitleSummaryRowDTO,
    UpdatedCountResponse,
)

router = APIRouter()

RESERVED_CATEGORY_NAMES = {"Uncategorized", calculations.IGNORED_CATEGORY}


@router.get("")
def list_categories(player: CurrentPlayer = Depends(get_current_player)) -> CategoryListResponse:
    names = db.list_categories(player.player_id)
    counts = db.get_category_counts(player.player_id)
    return CategoryListResponse(categories=[CategoryDTO(name=n, entry_count=counts.get(n, 0)) for n in names])


@router.post("", status_code=201)
def create_category(
    body: CreateCategoryRequest, player: CurrentPlayer = Depends(get_current_player)
) -> CategoryNameResponse:
    name = body.name.strip()
    if not name:
        raise ApiError(400, "Name is required.", "invalid_request")
    if name in RESERVED_CATEGORY_NAMES:
        raise ApiError(409, f"'{name}' is reserved and can't be used as a custom category.", "reserved_name")
    if not db.add_category(player.player_id, name):
        raise ApiError(409, f"'{name}' already exists.", "already_exists")
    return CategoryNameResponse(name=name)


@router.delete("/{name}", status_code=204)
def delete_category(name: str, player: CurrentPlayer = Depends(get_current_player)) -> None:
    if not db.delete_category(player.player_id, name):
        raise ApiError(409, f"'{name}' is still used by log entries and can't be deleted.", "category_in_use")


@router.get("/title-summary")
def title_summary(
    filter_category: str | None = Query(default=None, alias="filterCategory"),
    player: CurrentPlayer = Depends(get_current_player),
) -> TitleSummaryResponse:
    rows = db.get_title_category_summary(player.player_id, filter_category)
    return TitleSummaryResponse(
        rows=[
            TitleSummaryRowDTO(
                title=r["title"],
                category=r["app_category"],
                entry_count=r["c"],
                example_amount=r["example_amount"],
                amount_sign=r["amount_sign"],
            )
            for r in rows
        ]
    )


@router.post("/reassign")
def reassign(
    body: ReassignCategoryRequest, player: CurrentPlayer = Depends(get_current_player)
) -> UpdatedCountResponse:
    count = db.reassign_category(player.player_id, body.title, body.from_category, body.to_category)
    if body.title:
        db.upsert_category_rule(player.player_id, body.title, body.to_category)
        if body.amount_sign is not None:
            db.upsert_category_sign(player.player_id, body.title, body.to_category, body.amount_sign)
            db.apply_amount_sign(player.player_id, body.title, body.amount_sign)
    return UpdatedCountResponse(updated_count=count)
