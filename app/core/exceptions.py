"""Custom exception classes for the application."""

from typing import Any, Dict, Optional


class APIException(Exception):
    """Base exception class for API-related errors."""
    
    def __init__(
        self, 
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class NotFoundError(APIException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class AuthenticationError(APIException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(APIException):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class ConflictError(APIException):
    """Exception raised for resource conflicts."""
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status_code=409)


class DatabaseError(APIException):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status_code=500)