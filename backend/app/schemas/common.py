"""Shared schema helpers."""

from pydantic import BaseModel


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def build(cls, page: int, page_size: int, total: int) -> "PageMeta":
        total_pages = (total + page_size - 1) // page_size if total else 0
        return cls(page=page, page_size=page_size, total=total, total_pages=total_pages)
