"""Tests covering the system health endpoints."""

from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies import get_db_session
from app.core.config import settings
from main import create_application


def test_health_summary_exposes_compliance_checks(client_with_db):
    """The aggregated health endpoint should surface structured subsystem data."""

    response = client_with_db.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "timestamp" in payload
    assert "version" in payload
    assert "checks" in payload and isinstance(payload["checks"], dict)

    checks = payload["checks"]
    for expected_section in {"database", "system", "configuration", "module"}:
        assert expected_section in checks

    # timestamp should be ISO8601 compatible
    datetime.fromisoformat(payload["timestamp"])  # raises ValueError if invalid


def test_health_summary_includes_process_when_debug(monkeypatch, client_with_db):
    """Process metadata is only included for debugging scenarios."""

    monkeypatch.setattr(settings, "DEBUG", True)

    response = client_with_db.get("/api/v1/health")
    assert response.status_code == 200

    system_check = response.json()["checks"]["system"]
    assert "process" in system_check
    assert "pid" not in system_check.get("process", {})


def test_health_summary_hides_process_details_when_not_debug(
    monkeypatch, client_with_db
):
    """Process identifiers should be omitted from health payloads by default."""

    monkeypatch.setattr(settings, "DEBUG", False)

    response = client_with_db.get("/api/v1/health")
    assert response.status_code == 200

    system_check = response.json()["checks"]["system"]
    assert "process" not in system_check


@pytest.mark.smoke
def test_liveness_probe_returns_current_status(client):
    """Liveness probe should answer quickly with a timestamp."""

    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    datetime.fromisoformat(payload["timestamp"])


@pytest.mark.smoke
def test_readiness_probe_validates_database(client_with_db):
    """Readiness probe should confirm connectivity to the database."""

    response = client_with_db.get("/api/v1/health/readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
    datetime.fromisoformat(payload["timestamp"])


def test_health_summary_degrades_when_audit_logging_disabled(
    monkeypatch, client_with_db
):
    """Disabling audit logging should surface as a degraded configuration check."""

    monkeypatch.setattr(settings, "AUDIT_LOG_ENABLED", False)

    response = client_with_db.get("/api/v1/health")
    assert response.status_code == 200

    configuration_check = response.json()["checks"]["configuration"]
    assert configuration_check["audit_log_enabled"] is False
    assert configuration_check["status"].lower() in {"degraded", "unhealthy"}


def test_readiness_probe_returns_service_unavailable_when_db_fails():
    """The readiness probe should return 503 if the database check raises an error."""

    failing_app = create_application()

    class _FailingSession:
        async def execute(self, *_args, **_kwargs):  # noqa: D401 - stub behaviour
            raise RuntimeError("database offline")

    async def _get_failing_session():
        return _FailingSession()

    failing_app.dependency_overrides[get_db_session] = _get_failing_session

    with TestClient(failing_app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health/readiness")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()["detail"]
    assert body["status"] == "unhealthy"
    assert "database offline" in body["error"]
