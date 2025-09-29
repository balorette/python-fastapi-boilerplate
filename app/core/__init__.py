"""Core package initialization."""
from .config import get_settings, settings
from .health import get_system_health
from .logging import (
    HANDLER_APP_JSON,
    HANDLER_AUDIT_JSON,
    HANDLER_CONSOLE,
    HANDLER_ERROR_JSON,
    get_logger,
    log_audit_event,
    log_safety_event,
    setup_logging,
)

__all__ = [
    "get_settings",
    "settings",
    "get_system_health",
    "setup_logging",
    "get_logger",
    "log_safety_event",
    "log_audit_event",
    "HANDLER_CONSOLE",
    "HANDLER_APP_JSON",
    "HANDLER_AUDIT_JSON",
    "HANDLER_ERROR_JSON",
]
