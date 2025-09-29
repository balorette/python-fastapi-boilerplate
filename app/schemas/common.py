"""Shared Pydantic helpers used by the boilerplate application."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema that enforces strict validation and JSON encoding rules."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda value: value.isoformat() if value else None,
        },
    )


class PaginationParams(BaseSchema):
    """Pagination parameters accepted by list endpoints."""

    page: int = Field(1, ge=1, le=10_000, description="Page number (1-indexed)")
    size: int = Field(50, ge=1, le=1_000, description="Number of items per page")

    @property
    def offset(self) -> int:
        """Return the database offset for the current page."""

        return (self.page - 1) * self.size


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response wrapper with metadata helpers."""

    items: List[T] = Field(..., description="Items returned for this page")
    total: int = Field(..., ge=0, description="Total number of matching items")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Configured page size")
    pages: int = Field(..., ge=0, description="Total number of pages available")
    has_next: bool = Field(..., description="Whether another page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")

    @classmethod
    def create(
        cls,
        *,
        items: List[T],
        total: int,
        pagination: PaginationParams,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response from collection metadata."""

        pages = (total + pagination.size - 1) // pagination.size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages,
            has_next=pagination.page < pages,
            has_prev=pagination.page > 1,
        )


class ErrorResponse(BaseSchema):
    """Standardized error payload returned by exception handlers."""

    error: str = Field(..., description="Machine readable error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional context about the error",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the error was generated",
    )
    request_id: Optional[str] = Field(
        None,
        description="Request correlation identifier when available",
    )


class HealthCheck(BaseSchema):
    """Health check response schema shared across endpoints and tests."""

    status: str = Field(..., pattern=r"^(healthy|degraded|unhealthy)$")
    timestamp: datetime = Field(..., description="Timestamp of the health snapshot")
    version: str = Field(..., description="Application version string")
    checks: Dict[str, Any] = Field(..., description="Subsystem status breakdown")
    uptime_seconds: int = Field(..., ge=0, description="Service uptime in seconds")


class AuditInfo(BaseSchema):
    """Audit metadata commonly associated with domain resources."""

    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    created_by: Optional[str] = Field(None)
    updated_by: Optional[str] = Field(None)
    version: int = Field(..., ge=1)


class FilterParams(BaseSchema):
    """Common filter parameters used by list APIs."""

    search: Optional[str] = Field(None, min_length=1, max_length=255)
    active_only: bool = Field(True)
    created_after: Optional[datetime] = Field(None)
    created_before: Optional[datetime] = Field(None)

    @field_validator("created_after", "created_before")
    @classmethod
    def _validate_dates(cls, value: Optional[datetime]) -> Optional[datetime]:
        """Ensure provided dates are not in the future."""

        if value is None:
            return value
        if value > datetime.utcnow():
            raise ValueError("Filter date cannot be in the future")
        return value