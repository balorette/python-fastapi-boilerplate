"""
Health monitoring API endpoints for Astraeus.
SPEC COMPLIANCE: docs/ai/spec.md Section 5.1 - System Health Monitoring
ARCHITECTURE: docs/ai/architecture.md - Health Check and Observability
SAFETY: Provides runtime assurances for mission critical drone operations
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import psutil

from app.api.dependencies import get_db_session
from app.core.config import get_settings
from app.core.health import get_system_health
from app.schemas.common import HealthCheck as HealthCheckSchema

router = APIRouter()


async def _collect_database_check(session: AsyncSession) -> Dict[str, Any]:
    """Gather health indicators for the primary database."""
    started = time.perf_counter()
    check: Dict[str, Any] = {"status": "unhealthy"}

    try:
        await session.execute(text("SELECT 1"))
        check["response_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
        check["status"] = "healthy"
    except Exception as exc:  # pragma: no cover - captured in failure tests
        check["error"] = str(exc)
        return check

    bind = session.get_bind()
    if bind is not None:
        check["dialect"] = bind.dialect.name
        check["driver"] = bind.driver

        if bind.dialect.name.startswith("postgresql"):
            stats_query = text(
                """
                SELECT
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_hit,
                    blks_read
                FROM pg_stat_database
                WHERE datname = current_database()
                """
            )
            try:
                result = await session.execute(stats_query)
                row = result.fetchone()
                if row:
                    check["postgresql"] = {
                        "num_backends": row.numbackends,
                        "xact_commit": row.xact_commit,
                        "xact_rollback": row.xact_rollback,
                        "block_hit_rate": _calculate_block_hit_rate(row.blks_hit, row.blks_read),
                    }
                else:
                    check["postgresql"] = {
                        "available": False,
                        "reason": "pg_stat_database returned no rows",
                    }
            except Exception as exc:  # pragma: no cover - depends on permissions
                check["postgresql"] = {
                    "available": False,
                    "reason": f"pg_stat_database unavailable: {exc}",
                }
        else:
            check["postgresql"] = {
                "available": False,
                "reason": "Database dialect does not expose pg_stat_database",
            }

    return check


def _calculate_block_hit_rate(block_hits: int | None, block_reads: int | None) -> float:
    """Calculate PostgreSQL cache hit ratio when statistics are available."""
    hits = float(block_hits or 0)
    reads = float(block_reads or 0)
    total = hits + reads
    if total == 0:
        return 100.0
    return round((hits / total) * 100, 2)


def _collect_system_metrics() -> Dict[str, Any]:
    """Gather process and host level metrics via psutil."""
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_percent = psutil.cpu_percent(interval=0.1)
        process = psutil.Process()

        status = "healthy"
        warnings = []

        if memory.percent >= 90 or disk.percent >= 95 or cpu_percent >= 95:
            status = "unhealthy"
            warnings.append("Resource usage exceeds critical thresholds")
        elif memory.percent >= 80 or disk.percent >= 90 or cpu_percent >= 85:
            status = "degraded"
            warnings.append("Resource usage approaching critical thresholds")

        return {
            "status": status,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "warnings": warnings,
            "process": {
                "pid": process.pid,
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "threads": process.num_threads(),
            },
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        return {
            "status": "unknown",
            "error": str(exc),
        }


def _collect_configuration_check(settings) -> Dict[str, Any]:
    """Summarise configuration flags that affect runtime safety."""
    status = "healthy"
    warnings = []

    if not settings.audit_log_enabled:
        status = "degraded"
        warnings.append("Audit logging disabled - compliance risk")

    if not settings.safety_checks_enabled:
        status = "unhealthy"
        warnings.append("Safety checks disabled - unsafe for production")

    return {
        "status": status,
        "environment": settings.environment,
        "debug": settings.debug,
        "audit_log_enabled": settings.audit_log_enabled,
        "safety_checks_enabled": settings.safety_checks_enabled,
        "prometheus_metrics_enabled": settings.prometheus_metrics_enabled,
        "warnings": warnings,
    }


def _derive_overall_status(checks: Dict[str, Dict[str, Any]]) -> str:
    """Derive overall status from component checks."""
    severity_order = {
        "healthy": 0,
        "ready": 0,
        "alive": 0,
        "degraded": 1,
        "warning": 1,
        "unknown": 1,
        "unhealthy": 2,
        "error": 2,
        "down": 2,
        "not_ready": 2,
    }

    max_severity = 0
    for check in checks.values():
        status = str(check.get("status", "unknown")).lower()
        max_severity = max(max_severity, severity_order.get(status, 1))

    if max_severity >= 2:
        return "unhealthy"
    if max_severity == 1:
        return "degraded"
    return "healthy"


def _uptime_seconds() -> int:
    """Return process uptime in seconds."""
    try:
        process = psutil.Process()
        return int(time.time() - process.create_time())
    except Exception:  # pragma: no cover - defensive
        return 0


@router.get(
    "",
    response_model=HealthCheckSchema,
    summary="Aggregate system health",
    description="Aggregated health information including database latency, system metrics, and configuration flags.",
)
async def health_summary(session: AsyncSession = Depends(get_db_session)) -> HealthCheckSchema:
    """Return aggregated health information for the platform."""
    settings = get_settings()

    database_check = await _collect_database_check(session)
    system_metrics = _collect_system_metrics()
    configuration_check = _collect_configuration_check(settings)

    try:
        module_snapshot = await get_system_health()
        module_check = {
            "status": module_snapshot.get("overall_status", "unknown"),
            "components": module_snapshot.get("components", {}),
            "metrics": module_snapshot.get("metrics", {}),
            "alerts": module_snapshot.get("alerts", []),
        }
    except Exception as exc:  # pragma: no cover - defensive
        module_check = {"status": "unhealthy", "error": str(exc)}

    checks: Dict[str, Dict[str, Any]] = {
        "database": database_check,
        "system": system_metrics,
        "configuration": configuration_check,
        "module": module_check,
    }

    overall_status = _derive_overall_status(checks)

    return HealthCheckSchema(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=settings.app_version,
        checks=checks,
        uptime_seconds=_uptime_seconds(),
    )


@router.get(
    "/liveness",
    summary="Liveness probe",
    description="Kubernetes liveness probe for Astraeus.",
)
async def liveness_probe() -> Dict[str, Any]:
    """Simple liveness probe indicating the API process is running."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/readiness",
    summary="Readiness probe",
    description="Kubernetes readiness probe verifying downstream dependencies.",
)
async def readiness_probe(session: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Readiness probe that ensures the database is reachable."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
