"""The list envelope every list endpoint returns."""

from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
