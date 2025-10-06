"""Custom exception classes for the application."""

from typing import Any


class APIError(Exception):
    """Base exception class for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Exception raised for validation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=400, details=details)


class NotFoundError(APIError):
    """Exception raised when a resource is not found."""

    def __init__(
        self, message: str = "Resource not found", details: dict[str, Any] | None = None
    ):
        super().__init__(message, status_code=404, details=details)


class AuthenticationError(APIError):
    """Exception raised for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=401, details=details)


class AuthorizationError(APIError):
    """Exception raised for authorization errors."""

    def __init__(
        self, message: str = "Access denied", details: dict[str, Any] | None = None
    ):
        super().__init__(message, status_code=403, details=details)


class ConflictError(APIError):
    """Exception raised for resource conflicts."""

    def __init__(
        self, message: str = "Resource conflict", details: dict[str, Any] | None = None
    ):
        super().__init__(message, status_code=409, details=details)


class DatabaseError(APIError):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, status_code=500, details=details)
