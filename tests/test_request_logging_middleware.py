"""Regression coverage for the structured request logging middleware."""

from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware import RequestLoggingMiddleware
from app.core.logging import setup_logging


class _ListHandler(logging.Handler):
    """Collect log records for assertions without touching disk handlers."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401 - simple collector
        self.records.append(record)


def test_request_logging_emits_correlation_metadata(tmp_path):
    """The middleware should emit structured correlation metadata for each request."""

    setup_logging("INFO", log_directory=tmp_path)

    test_app = FastAPI()
    test_app.add_middleware(
        RequestLoggingMiddleware,
        correlation_header_name="X-Test-Correlation",
        process_time_header_name="X-Test-Elapsed",
    )

    @test_app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    middleware_logger = logging.getLogger("app.middleware")
    handler = _ListHandler()
    middleware_logger.addHandler(handler)

    try:
        with TestClient(test_app) as client:
            response = client.get("/ping")
    finally:
        middleware_logger.removeHandler(handler)

    assert response.status_code == 200
    correlation_id = response.headers["X-Test-Correlation"]
    assert float(response.headers["X-Test-Elapsed"]) >= 0.0

    start_record = next(
        record for record in handler.records if record.getMessage() == "Request started"
    )
    complete_record = next(
        record
        for record in handler.records
        if record.getMessage() == "Request completed"
    )

    assert start_record.correlation_id == correlation_id
    assert start_record.request_id == correlation_id
    assert complete_record.correlation_id == correlation_id
    assert complete_record.request_id == correlation_id
    assert complete_record.process_time_ms >= 0
