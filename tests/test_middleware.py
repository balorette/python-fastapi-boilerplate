"""Tests covering the middleware stack configured for the boilerplate app."""

from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.middleware import (
    PerformanceMonitoringMiddleware,
    RateLimitingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from main import app


def test_middleware_registration_and_observability_headers():
    """The FastAPI app should include the middleware stack in the documented order."""

    middleware_classes = [middleware.cls for middleware in app.user_middleware]
    expected_order = [
        CORSMiddleware,
        TrustedHostMiddleware,
        SecurityHeadersMiddleware,
        PerformanceMonitoringMiddleware,
        RequestLoggingMiddleware,
        RateLimitingMiddleware,
    ]

    assert middleware_classes[: len(expected_order)] == list(reversed(expected_order))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers.get("X-Correlation-ID")
    process_time_header = response.headers.get("X-Process-Time")
    assert process_time_header is not None
    assert float(process_time_header) >= 0.0
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


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