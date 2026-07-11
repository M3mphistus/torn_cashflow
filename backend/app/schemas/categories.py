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


class TitleSummaryResponse(CamelModel):
    rows: list[TitleSummaryRowDTO]


class ReassignCategoryRequest(CamelModel):
    title: str
    from_category: str
    to_category: str


class UpdatedCountResponse(CamelModel):
    updated_count: int
