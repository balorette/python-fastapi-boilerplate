"""Tests covering the system health endpoints."""

from datetime import datetime


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


def test_liveness_probe_returns_current_status(client):
    """Liveness probe should answer quickly with a timestamp."""

    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    datetime.fromisoformat(payload["timestamp"])


def test_readiness_probe_validates_database(client_with_db):
    """Readiness probe should confirm connectivity to the database."""

    response = client_with_db.get("/api/v1/health/readiness")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
    datetime.fromisoformat(payload["timestamp"])
