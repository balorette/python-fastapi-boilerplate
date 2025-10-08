"""Structured exception handlers for the FastAPI application."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.repositories.base import DataIntegrityError
from app.schemas.common import ErrorResponse
from app.services.base import (
    BusinessRuleViolationError,
    DuplicateEntityError,
    EntityNotFoundError,
    SafetyViolationError,
    ServiceError,
)

logger = logging.getLogger(__name__)

HTTP_422_STATUS = status.HTTP_422_UNPROCESSABLE_CONTENT


def _request_id_from(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _json_response(
    *,
    request: Request,
    status_code: int,
    error: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=error,
        message=message,
        details=details,
        request_id=_request_id_from(request),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


async def entity_not_found_handler(
    request: Request, exc: EntityNotFoundError
) -> JSONResponse:
    logger.warning("Entity not found", extra={"error": str(exc)})
    return _json_response(
        request=request,
        status_code=status.HTTP_404_NOT_FOUND,
        error="not_found",
        message=str(exc),
    )


async def duplicate_entity_handler(
    request: Request, exc: DuplicateEntityError
) -> JSONResponse:
    logger.warning("Duplicate entity", extra={"error": str(exc)})
    return _json_response(
        request=request,
        status_code=status.HTTP_409_CONFLICT,
        error="duplicate_entity",
        message=str(exc),
    )


async def business_rule_handler(
    request: Request, exc: BusinessRuleViolationError
) -> JSONResponse:
    logger.warning("Business rule violation", extra={"error": str(exc)})
    return _json_response(
        request=request,
        status_code=HTTP_422_STATUS,
        error="business_rule_violation",
        message=str(exc),
    )


async def safety_violation_handler(
    request: Request, exc: SafetyViolationError
) -> JSONResponse:
    logger.error("Safety violation", extra={"error": str(exc)})
    return _json_response(
        request=request,
        status_code=status.HTTP_400_BAD_REQUEST,
        error="safety_violation",
        message=str(exc),
        details={"severity": "critical"},
    )


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    logger.error("Service error", exc_info=True, extra={"error": str(exc)})
    return _json_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="service_error",
        message=str(exc),
    )


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Request validation error", extra={"errors": exc.errors()})
    return _json_response(
        request=request,
        status_code=HTTP_422_STATUS,
        error="request_validation_error",
        message="Request validation failed",
        details={"errors": exc.errors()},
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    logger.error("Integrity error", exc_info=True)
    message = str(exc.orig) if exc.orig else str(exc)
    lowered = message.lower()
    if "unique" in lowered:
        error = "integrity_unique_violation"
        response_message = "A record with this information already exists"
        status_code = status.HTTP_409_CONFLICT
    elif "foreign" in lowered:
        error = "integrity_foreign_key_violation"
        response_message = "Referenced record does not exist"
        status_code = HTTP_422_STATUS
    else:
        error = "integrity_error"
        response_message = "Data integrity constraint violated"
        status_code = HTTP_422_STATUS

    return _json_response(
        request=request,
        status_code=status_code,
        error=error,
        message=response_message,
        details={"original_message": message},
    )


async def data_integrity_error_handler(
    request: Request, exc: DataIntegrityError
) -> JSONResponse:
    logger.error("Repository data integrity error", extra={"error": str(exc)})
    return _json_response(
        request=request,
        status_code=HTTP_422_STATUS,
        error="data_integrity_violation",
        message=str(exc),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return _json_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="internal_server_error",
        message="An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all structured exception handlers on the application."""

    handlers = {
        EntityNotFoundError: entity_not_found_handler,
        DuplicateEntityError: duplicate_entity_handler,
        BusinessRuleViolationError: business_rule_handler,
        SafetyViolationError: safety_violation_handler,
        ServiceError: service_error_handler,
        RequestValidationError: request_validation_handler,
        IntegrityError: integrity_error_handler,
        DataIntegrityError: data_integrity_error_handler,
        Exception: generic_exception_handler,
    }

    for exception_type, handler in handlers.items():
        app.add_exception_handler(exception_type, handler)
