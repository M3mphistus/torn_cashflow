from .common import CamelModel


class CategoryDTO(CamelModel):
    name: str
    entry_count: int


class CategoryListResponse(CamelModel):
    categories: list[CategoryDTO]


class CreateCategoryRequest(CamelModel):
    name: str


class CategoryNameResponse(CamelModel):
    name: str


class TitleSummaryRowDTO(CamelModel):
    title: str | None
    category: str
    entry_count: int
    example_amount: float | None = None
    amount_sign: int | None = None


class TitleSummaryResponse(CamelModel):
    rows: list[TitleSummaryRowDTO]


class ReassignCategoryRequest(CamelModel):
    title: str
    from_category: str
    to_category: str
    amount_sign: int | None = None


class UpdatedCountResponse(CamelModel):
    updated_count: int
