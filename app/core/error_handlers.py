"""Global error handlers for the application."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import APIException, DatabaseError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers with the FastAPI app."""

    @app.exception_handler(APIException)
    async def api_exception_handler(
        request: Request, exc: APIException
    ) -> JSONResponse:
        """Handle custom API exceptions."""
        logger.error(
            "API Exception: %s - Path: %s",
            exc.message,
            request.url.path,
            extra={
                "status_code": exc.status_code,
                "details": exc.details,
                "path": str(request.url.path),
                "method": request.method,
            },
        )

        content = {
            "error": {
                "message": exc.message,
                "status_code": exc.status_code,
                "details": exc.details,
            }
        }

        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle SQLAlchemy database errors."""
        logger.error(
            "Database error: %s - Path: %s",
            str(exc),
            request.url.path,
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "error_type": type(exc).__name__,
            },
        )

        database_error = DatabaseError("Database operation failed")
        content = {
            "error": {
                "message": database_error.message,
                "status_code": database_error.status_code,
                "details": database_error.details,
            }
        }

        return JSONResponse(status_code=database_error.status_code, content=content)

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all other unhandled exceptions."""
        logger.error(
            "Unhandled exception: %s - Path: %s",
            str(exc),
            request.url.path,
            extra={
                "path": str(request.url.path),
                "method": request.method,
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )

        content = {
            "error": {
                "message": "Internal server error",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {},
            }
        }

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=content
        )
