"""Pagination schemas for API responses."""

from typing import TypeVar

from pydantic import BaseModel, Field, field_validator

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""

    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of records to return"
    )
    order_by: str | None = Field(
        None, description="Field to order by (prefix with - for desc)"
    )

    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, v):
        if v is not None:
            # Remove the leading - if present for validation
            field_name = v[1:] if v.startswith("-") else v
            # Basic validation - in a real app you'd check against allowed fields
            if not field_name.isalnum() and "_" not in field_name:
                raise ValueError("Invalid order_by field format")
        return v


class SearchParams(PaginationParams):
    """Search parameters with pagination."""

    query: str = Field(
        ..., min_length=1, max_length=255, description="Search query string"
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        # Basic sanitization
        return v.strip()


class FilterParams(PaginationParams):
    """Advanced filtering parameters."""

    filters: dict | None = Field(None, description="Dynamic filters")

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v):
        if v is not None:
            # Validate filter structure
            for key, _value in v.items():
                if not isinstance(key, str):
                    raise ValueError("Filter keys must be strings")
                # Add more validation as needed
        return v


class PaginatedResponse[T](BaseModel):
    """Generic paginated response wrapper."""

    items: list[T] = Field(..., description="List of items")
    total: int = Field(..., ge=0, description="Total number of items")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Maximum items per page")
    has_next: bool = Field(..., description="Whether there are more items")
    has_prev: bool = Field(..., description="Whether there are previous items")
    page: int = Field(..., ge=1, description="Current page number")
    total_pages: int = Field(..., ge=1, description="Total number of pages")

    @classmethod
    def create(
        cls, items: list[T], total: int, skip: int = 0, limit: int = 100
    ) -> "PaginatedResponse[T]":
        """Create a paginated response with calculated fields."""
        page = (skip // limit) + 1
        total_pages = max(1, (total + limit - 1) // limit)
        has_next = skip + limit < total
        has_prev = skip > 0

        return cls(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev,
            page=page,
            total_pages=total_pages,
        )


class DateRangeParams(BaseModel):
    """Date range filtering parameters."""

    start_date: str | None = Field(None, description="Start date (ISO format)")
    end_date: str | None = Field(None, description="End date (ISO format)")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v):
        if v is not None:
            try:
                from datetime import datetime

                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(
                    "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                ) from None
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        if (
            v is not None
            and info.data
            and "start_date" in info.data
            and info.data["start_date"] is not None
        ):
            from datetime import datetime

            start = datetime.fromisoformat(
                info.data["start_date"].replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if end < start:
                raise ValueError("end_date must be after start_date")
        return v
