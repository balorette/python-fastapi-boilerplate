"""Application package initialization."""

__version__ = "0.1.0"


from .core import (
    HANDLER_APP_JSON,
    HANDLER_AUDIT_JSON,
    HANDLER_CONSOLE,
    HANDLER_ERROR_JSON,
    get_logger,
    get_settings,
    log_audit_event,
    log_safety_event,
    settings,
    setup_logging,
)

__all__ = [
    "settings",
    "get_settings",
    "setup_logging",
    "get_logger",
    "log_safety_event",
    "log_audit_event",
    "HANDLER_CONSOLE",
    "HANDLER_APP_JSON",
    "HANDLER_AUDIT_JSON",
    "HANDLER_ERROR_JSON",
]
