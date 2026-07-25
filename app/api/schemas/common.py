"""Shared API response wrappers."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard success response envelope for consistent client parsing."""

    success: bool = True
    message: str = "OK"
    data: T | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    pages: int = 0


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    success: bool = False
    message: str
    details: dict | None = None
    request_id: str | None = None
