"""Shared/generic schemas."""
from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A generic paginated response envelope."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        pages = ceil(total / page_size) if page_size else 0
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)
