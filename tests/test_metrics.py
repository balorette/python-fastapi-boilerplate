"""Tests for the optional Prometheus metrics endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from main import create_application


def test_metrics_endpoint_available_when_enabled(monkeypatch):
    """Enabling metrics should expose the Prometheus scrape endpoint."""

    monkeypatch.setattr(settings, "PROMETHEUS_METRICS_ENABLED", True)

    app = create_application()
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# HELP" in response.text


def test_metrics_endpoint_absent_when_disabled():
    """Metrics route should not exist when the toggle is disabled."""

    app = create_application()
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 404
