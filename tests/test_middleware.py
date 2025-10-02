"""Tests covering the middleware stack configured for the boilerplate app."""

import logging

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.middleware import (
    PerformanceMonitoringMiddleware,
    RateLimitingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.config import settings
from main import app, create_application


def test_middleware_registration_and_observability_headers():
    """The FastAPI app should include the middleware stack in the documented order."""

    fresh_app = create_application()
    middleware_classes = [middleware.cls for middleware in fresh_app.user_middleware]

    expected_order = [CORSMiddleware, TrustedHostMiddleware]
    if settings.SECURITY_HEADERS_ENABLED:
        expected_order.append(SecurityHeadersMiddleware)
    if settings.PERFORMANCE_MONITORING_ENABLED:
        expected_order.append(PerformanceMonitoringMiddleware)
    if settings.REQUEST_LOGGING_ENABLED:
        expected_order.append(RequestLoggingMiddleware)
    if settings.RATE_LIMIT_ENABLED:
        expected_order.append(RateLimitingMiddleware)

    assert middleware_classes[: len(expected_order)] == list(reversed(expected_order))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get(settings.REQUEST_ID_HEADER_NAME)
    process_time_header = response.headers.get(settings.PROCESS_TIME_HEADER_NAME)
    assert process_time_header is not None
    assert float(process_time_header) >= 0.0
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_security_headers_allow_fastapi_docs_assets():
    """CSP should permit FastAPI's Swagger/ReDoc assets served from jsDelivr."""

    app_with_security = create_application()
    with TestClient(app_with_security) as client:
        response = client.get(f"{settings.API_V1_STR}/docs")

    csp_header = response.headers.get("Content-Security-Policy")
    assert csp_header is not None
    assert "https://cdn.jsdelivr.net" in csp_header
    assert "'unsafe-inline'" in csp_header


def test_security_headers_remain_strict_for_api_routes():
    """Non-doc routes should receive the hardened CSP without external CDNs."""

    app_with_security = create_application()
    with TestClient(app_with_security) as client:
        response = client.get("/api/v1/health/liveness")

    csp_header = response.headers.get("Content-Security-Policy")
    assert csp_header is not None
    assert "https://cdn.jsdelivr.net" not in csp_header
    assert "script-src 'self'" in csp_header
    assert "'unsafe-inline'" not in csp_header


def test_request_logging_emits_correlation_id():
    """Request logging middleware should persist correlation IDs into log records."""

    app_with_logging = create_application()

    class _MemoryHandler(logging.Handler):
        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    with TestClient(app_with_logging) as client:
        handler = _MemoryHandler()
        middleware_logger = logging.getLogger("app.middleware")
        middleware_logger.addHandler(handler)
        try:
            response = client.get("/api/v1/health/liveness")
        finally:
            middleware_logger.removeHandler(handler)

    correlation_id = response.headers.get(settings.REQUEST_ID_HEADER_NAME)
    assert correlation_id, "Expected correlation header"

    completed_records = [
        record for record in handler.records if record.getMessage() == "Request completed"
    ]
    assert completed_records, "Expected completion log entry"
    assert any(getattr(record, "request_id", None) == correlation_id for record in completed_records)


def test_request_logging_respects_custom_header_names(monkeypatch):
    """Custom header names from settings should appear in responses."""

    monkeypatch.setattr(settings, "REQUEST_ID_HEADER_NAME", "X-Test-Request-ID")
    monkeypatch.setattr(settings, "PROCESS_TIME_HEADER_NAME", "X-Test-Duration")

    app_with_logging = create_application()
    with TestClient(app_with_logging) as client:
        response = client.get("/api/v1/health/liveness")

    assert "X-Test-Request-ID" in response.headers
    assert "X-Test-Duration" in response.headers


def test_rate_limiting_respects_custom_exempt_paths(monkeypatch):
    """Exempt paths should bypass rate limiting even under heavy traffic."""

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_EXEMPT_PATHS", ("/api/v1/health/liveness",))

    app_with_limit = create_application()
    with TestClient(app_with_limit) as client:
        first = client.get("/api/v1/health/liveness")
        second = client.get("/api/v1/health/liveness")

    assert first.status_code == 200
    assert second.status_code == 200


def test_rate_limiting_returns_429_for_excessive_requests():
    """The rate limiting middleware should return HTTP 429 when the limit is exceeded."""

    limited_app = FastAPI()
    limited_app.add_middleware(CORSMiddleware, allow_origins=["*"])
    limited_app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    limited_app.add_middleware(SecurityHeadersMiddleware)
    limited_app.add_middleware(PerformanceMonitoringMiddleware)
    limited_app.add_middleware(RequestLoggingMiddleware)
    limited_app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=1,
        exempt_paths=(),
    )

    @limited_app.get("/limited")
    def limited() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(limited_app, raise_server_exceptions=False)

    first_response = client.get("/limited")
    assert first_response.status_code == status.HTTP_200_OK

    second_response = client.get("/limited")
    assert second_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert second_response.json()["detail"] == "Rate limit exceeded"


def test_middlewares_can_be_disabled_via_settings(monkeypatch):
    """Configuration flags should allow disabling optional middleware components."""

    monkeypatch.setattr(settings, "SECURITY_HEADERS_ENABLED", False)
    monkeypatch.setattr(settings, "PERFORMANCE_MONITORING_ENABLED", False)
    monkeypatch.setattr(settings, "REQUEST_LOGGING_ENABLED", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    disabled_app = create_application()
    middleware_classes = {middleware.cls for middleware in disabled_app.user_middleware}

    assert SecurityHeadersMiddleware not in middleware_classes
    assert PerformanceMonitoringMiddleware not in middleware_classes
    assert RequestLoggingMiddleware not in middleware_classes
    assert RateLimitingMiddleware not in middleware_classes
