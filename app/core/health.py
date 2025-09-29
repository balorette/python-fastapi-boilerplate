"""System health helpers reused by the health endpoints."""

from __future__ import annotations

import platform
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.config import settings


def _status_from_flags(*flags: bool) -> str:
    """Return ``healthy`` when all flags are true, otherwise ``degraded``."""

    return "healthy" if all(flags) else "degraded"


async def get_system_health() -> Dict[str, Any]:
    """Return component and feature flag health used by system endpoints."""

    logging_active = settings.audit_log_enabled and settings.safety_checks_enabled
    feature_flags: Dict[str, Any] = {
        "audit_logging": {
            "status": "healthy" if settings.audit_log_enabled else "degraded",
            "enabled": settings.audit_log_enabled,
        },
        "safety_checks": {
            "status": "healthy" if settings.safety_checks_enabled else "unhealthy",
            "enabled": settings.safety_checks_enabled,
        },
        "prometheus_metrics": {
            "status": "healthy"
            if settings.prometheus_metrics_enabled
            else "degraded",
            "enabled": settings.prometheus_metrics_enabled,
        },
    }

    platform_metrics = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
    }

    alerts: List[str] = []
    if not settings.audit_log_enabled:
        alerts.append("Audit logging disabled - enable for compliance tracking")
    if not settings.safety_checks_enabled:
        alerts.append("Safety checks disabled - re-enable before production")

    components: Dict[str, Any] = {
        "logging": {
            "status": "healthy" if logging_active else "degraded",
            "log_directory": settings.log_directory,
            "log_level": settings.LOG_LEVEL,
        },
        "feature_flags": {
            "status": _status_from_flags(
                settings.audit_log_enabled,
                settings.safety_checks_enabled,
            ),
            "flags": feature_flags,
        },
        "rate_limiting": {
            "status": "healthy" if settings.RATE_LIMIT_ENABLED else "degraded",
            "requests_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        },
        "cors": {
            "status": "healthy",
            "allow_origins": settings.CORS_ALLOW_ORIGINS,
        },
    }

    metrics = {
        "rate_limit_requests_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        "slow_request_threshold_ms": settings.PERFORMANCE_SLOW_REQUEST_THRESHOLD_MS,
    }

    overall_status = "healthy"
    for component in components.values():
        status = str(component.get("status", "healthy")).lower()
        if status == "unhealthy":
            overall_status = "unhealthy"
            break
        if status == "degraded" and overall_status != "unhealthy":
            overall_status = "degraded"

    return {
        "overall_status": overall_status,
        "components": components,
        "metrics": metrics | {"platform": platform_metrics},
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
