from __future__ import annotations

import logging
import logging.config
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings


HANDLER_CONSOLE = "console"
HANDLER_APP_JSON = "app_json"
HANDLER_AUDIT_JSON = "audit_json"
HANDLER_ERROR_JSON = "error_json"


def _iso_utc_timestamp() -> str:
    """Return an ISO 8601 timestamp with a trailing Z."""

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class StructuredLogFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that injects compliance metadata into each record."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        if "timestamp" not in log_record:
            log_record["timestamp"] = _iso_utc_timestamp()

        log_record.setdefault("service", settings.SERVICE_NAME)

        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id

        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        if hasattr(record, "safety_critical"):
            log_record["safety_critical"] = record.safety_critical

        if hasattr(record, "compliance_event"):
            log_record["compliance_event"] = record.compliance_event


class SafetyAuditFilter(logging.Filter):
    """Mark records that should be treated as safety or compliance events."""

    SAFETY_KEYWORDS = [
        "safety",
        "emergency",
        "malfunction",
        "compliance",
    ]

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - inherited documentation
        preflag = getattr(record, "safety_critical", None)

        if preflag is True:
            record.safety_critical = True
            return True

        message = record.getMessage().lower()
        is_safety_critical = any(keyword in message for keyword in self.SAFETY_KEYWORDS)

        if record.levelno >= logging.ERROR:
            is_safety_critical = True

        record.safety_critical = is_safety_critical
        return True


def setup_logging(
    log_level: str = "INFO",
    *,
    log_directory: Optional[Union[str, Path]] = None,
) -> None:
    """Configure the structured logging pipeline used by the application."""

    resolved_level = getattr(logging, log_level.upper(), logging.INFO)
    logs_path = Path(log_directory or settings.LOG_DIRECTORY)
    logs_path.mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": StructuredLogFormatter},
            "console": {
                "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {"safety_audit": {"()": SafetyAuditFilter}},
        "handlers": {
            HANDLER_CONSOLE: {
                "class": "logging.StreamHandler",
                "level": log_level.upper(),
                "formatter": "console" if settings.ENVIRONMENT == "development" else "json",
                "stream": sys.stdout,
                "filters": ["safety_audit"],
            },
            HANDLER_APP_JSON: {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": logs_path / "application.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 30,
                "filters": ["safety_audit"],
            },
            HANDLER_AUDIT_JSON: {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filename": logs_path / "audit.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 2555,
                "filters": ["safety_audit"],
            },
            HANDLER_ERROR_JSON: {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filename": logs_path / "errors.log",
                "when": "midnight",
                "interval": 1,
                "backupCount": 365,
                "filters": ["safety_audit"],
            },
        },
        "loggers": {
            "app": {
                "level": log_level.upper(),
                "handlers": [
                    HANDLER_CONSOLE,
                    HANDLER_APP_JSON,
                    HANDLER_AUDIT_JSON,
                ],
                "propagate": False,
            },
            "app.safety": {
                "level": "DEBUG",
                "handlers": [
                    HANDLER_CONSOLE,
                    HANDLER_APP_JSON,
                    HANDLER_AUDIT_JSON,
                    HANDLER_ERROR_JSON,
                ],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": [HANDLER_CONSOLE],
                "propagate": False,
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": [HANDLER_CONSOLE],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": [HANDLER_CONSOLE],
                "propagate": False,
            },
            "": {
                "level": "WARNING",
                "handlers": [HANDLER_CONSOLE, HANDLER_APP_JSON],
            },
        },
    }

    logging.config.dictConfig(config)

    logger = logging.getLogger(__name__)
    logger.info(
        "Structured logging configured",
        extra={
            "environment": settings.ENVIRONMENT,
            "log_level": log_level.upper(),
            "audit_enabled": settings.AUDIT_LOG_ENABLED,
            "safety_checks": settings.SAFETY_CHECKS_ENABLED,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance."""

    return logging.getLogger(name)


def log_safety_event(
    logger: logging.Logger,
    message: str,
    event_type: str,
    *,
    severity: str = "warning",
    **kwargs: Any,
) -> None:
    """Emit a safety event with standardized metadata."""

    extra_data = {
        "safety_critical": True,
        "compliance_event": True,
        "event_type": event_type,
        "timestamp": _iso_utc_timestamp(),
        **kwargs,
    }

    log_method = getattr(logger, severity.lower(), logger.warning)
    log_method(message, extra=extra_data)


def log_audit_event(
    logger: logging.Logger,
    action: str,
    resource_type: str,
    resource_id: str,
    *,
    user_id: Optional[str] = None,
    success: bool = True,
    **kwargs: Any,
) -> None:
    """Emit an audit event capturing the requested metadata."""

    extra_data = {
        "compliance_event": True,
        "audit_event": True,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "success": success,
        "timestamp": _iso_utc_timestamp(),
        **kwargs,
    }

    logger.info("Audit event", extra=extra_data)
