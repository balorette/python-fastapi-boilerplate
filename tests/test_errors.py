"""Tests covering the structured error handlers registered with FastAPI."""

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.api.middleware import RequestLoggingMiddleware
from app.services.base import (
    BusinessRuleViolationError,
    DuplicateEntityError,
    EntityNotFoundError,
)

HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)
    return app


def test_entity_not_found_handler_includes_request_id():
    """Handlers should emit the standardized payload with a request identifier."""

    app = _build_app()

    @app.get("/missing")
    async def missing_route():
        raise EntityNotFoundError("Widget not found")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/missing")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    payload = response.json()
    assert payload["error"] == "not_found"
    assert payload["message"] == "Widget not found"
    assert payload["request_id"]
    assert "timestamp" in payload


def test_duplicate_entity_handler_returns_conflict_status():
    """Duplicate entity errors should map to HTTP 409 with structured payloads."""

    app = _build_app()

    @app.get("/duplicate")
    async def duplicate_route():
        raise DuplicateEntityError("Widget already exists")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/duplicate")

    assert response.status_code == status.HTTP_409_CONFLICT
    payload = response.json()
    assert payload["error"] == "duplicate_entity"
    assert payload["message"] == "Widget already exists"


def test_business_rule_violation_maps_to_unprocessable_entity():
    """Business rule violations should surface as HTTP 422 with context."""

    app = _build_app()

    @app.get("/rule")
    async def rule_route():
        raise BusinessRuleViolationError("Safety checks failed")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/rule")

    assert response.status_code == HTTP_422_STATUS
    payload = response.json()
    assert payload["error"] == "business_rule_violation"
    assert payload["message"] == "Safety checks failed"
