"""Tests for the optional Prometheus metrics endpoint."""

from __future__ import annotations

import builtins
import sys

from fastapi.testclient import TestClient

from fastapi import FastAPI

from app.api.routes import metrics
from app.core.config import settings
from app.api.routes.metrics import attach_metrics_endpoint
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


def test_metrics_endpoint_logs_warning_when_dependency_missing(monkeypatch, caplog):
    """Missing prometheus_client dependency should log a warning and skip wiring."""

    monkeypatch.setattr(settings, "PROMETHEUS_METRICS_ENABLED", True)
    monkeypatch.delitem(sys.modules, "prometheus_client", raising=False)

    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "prometheus_client":
            raise ImportError("prometheus client not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)

    app = FastAPI()
    warnings: list[str] = []

    monkeypatch.setattr(
        metrics.logger, "warning", lambda message: warnings.append(message)
    )

    attach_metrics_endpoint(app)

    assert warnings and "prometheus_client is not installed" in warnings[-1]

    with TestClient(app) as client:
        assert client.get("/metrics").status_code == 404
