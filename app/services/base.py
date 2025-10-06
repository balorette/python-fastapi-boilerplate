"""Base service abstractions with audit-friendly logging helpers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.pagination import PaginatedResponse, PaginationParams


class ServiceError(Exception):
    """Base exception for service-layer failures."""


class BusinessRuleViolationError(ServiceError):
    """Raised when business logic constraints are violated."""


class EntityNotFoundError(ServiceError):
    """Raised when an expected entity cannot be located."""


class DuplicateEntityError(ServiceError):
    """Raised when attempting to create a duplicate entity."""


class SafetyViolationError(ServiceError):
    """Raised when safety or compliance rules are breached."""


class BaseService:
    """Shared base class providing audit-aware logging and validation helpers."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self.logger = logging.getLogger(f"app.services.{service_name}")

    def _log_operation(
        self,
        operation: str,
        *,
        entity_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        """Emit a structured log entry describing a successful operation."""

        context = {
            "service": self.service_name,
            "operation": operation,
            "entity_id": str(entity_id) if entity_id else None,
            "user_id": str(user_id) if user_id else None,
        }
        if extra_context:
            context.update(extra_context)
        self.logger.info("Service operation", extra=context)

    def _log_error(
        self,
        operation: str,
        error: Exception,
        *,
        entity_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        """Emit a structured error log describing a failed operation."""

        context = {
            "service": self.service_name,
            "operation": operation,
            "entity_id": str(entity_id) if entity_id else None,
            "user_id": str(user_id) if user_id else None,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        if extra_context:
            context.update(extra_context)
        self.logger.error("Service operation failed", extra=context)

    async def _validate_entity_exists(
        self,
        session: AsyncSession,
        repository: Any,
        entity_id: Any,
        *,
        entity_name: str = "Entity",
    ) -> Any:
        """Ensure an entity exists before proceeding with an operation."""

        entity = await repository.get_by_id(entity_id, session=session)
        if entity is None:
            raise EntityNotFoundError(f"{entity_name} with ID {entity_id} not found")
        return entity

    async def _validate_unique_field(
        self,
        session: AsyncSession,
        repository: Any,
        *,
        field_name: str,
        field_value: Any,
        exclude_id: Any | None = None,
        entity_name: str = "Entity",
    ) -> None:
        """Guard against duplicate values for fields that must be unique."""

        exists = await repository.exists(
            field_name=field_name,
            field_value=field_value,
            exclude_id=exclude_id,
            session=session,
        )
        if exists:
            raise DuplicateEntityError(
                f"{entity_name} with {field_name} '{field_value}' already exists"
            )

    def _validate_business_rules(
        self,
        rules: dict[str, bool],
        *,
        context: str = "Operation",
    ) -> None:
        """Raise an error if any provided business rules evaluate to ``False``."""

        violations = [rule for rule, passed in rules.items() if not passed]
        if violations:
            raise BusinessRuleViolationError(
                f"{context} failed business rule validation: {', '.join(violations)}"
            )

    def _build_audit_context(
        self,
        operation: str,
        *,
        user_id: UUID | str | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a dictionary suitable for audit logging metadata."""

        context: dict[str, Any] = {
            "operation": operation,
            "service": self.service_name,
            "user_id": str(user_id) if user_id else None,
        }
        if extra_context:
            context.update(extra_context)
        return context

    def _sanitize_update_data(
        self,
        update_data: dict[str, Any],
        *,
        allowed_fields: set[str] | None = None,
        forbidden_fields: set[str] | None = None,
    ) -> dict[str, Any]:
        """Strip forbidden keys and ``None`` values from update payloads."""

        sanitized = {
            key: value for key, value in update_data.items() if value is not None
        }
        if forbidden_fields:
            for field in forbidden_fields:
                sanitized.pop(field, None)
        if allowed_fields is not None:
            sanitized = {
                key: value for key, value in sanitized.items() if key in allowed_fields
            }
        return sanitized

    async def paginate(
        self,
        session: AsyncSession,
        repository: Any,
        *,
        pagination: PaginationParams,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        load_relationships: list[str] | None = None,
    ) -> PaginatedResponse[Any]:
        """Return a paginated response leveraging the repository helpers."""

        items = await repository.list(
            pagination=pagination,
            filters=filters,
            order_by=order_by,
            session=session,
            load_relationships=load_relationships,
        )
        total = await repository.count(filters=filters, session=session)
        return PaginatedResponse.create(
            items=items,
            total=total,
            skip=pagination.skip,
            limit=pagination.limit,
        )
