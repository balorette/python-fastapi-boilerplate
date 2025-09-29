"""Tests covering the structured logging helpers in the boilerplate."""

import logging

import pytest

from app.core.logging import (
    get_logger,
    log_audit_event,
    log_safety_event,
    setup_logging,
)


class _ListHandler(logging.Handler):
    """Collect log records for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401 - simple forwarder
        self.records.append(record)


@pytest.fixture
def configured_logger(tmp_path):
    """Provide a logger configured with the structured pipeline."""

    setup_logging("INFO", log_directory=tmp_path)
    logger = get_logger("app.safety")
    handler = _ListHandler()
    logger.addHandler(handler)

    try:
        yield logger, handler.records
    finally:
        logger.removeHandler(handler)


def test_get_logger_adds_safety_metadata(configured_logger):
    """Records emitted by configured loggers should include safety metadata."""

    logger, records = configured_logger
    logger.warning("Emergency landing due to weather conditions")

    assert records, "Expected a log record to be captured"
    record = records[-1]

    assert record.name == "app.safety"
    assert record.safety_critical is True


def test_log_safety_event_injects_metadata(tmp_path):
    """Safety helper should enrich events with compliance metadata."""

    setup_logging("INFO", log_directory=tmp_path)
    logger = get_logger("app.safety")
    handler = _ListHandler()
    logger.addHandler(handler)

    try:
        log_safety_event(
            logger,
            "Battery temperature exceeded safe threshold",
            "battery_overheat",
            fleet_id="alpha-1",
        )
    finally:
        logger.removeHandler(handler)

    assert handler.records, "Expected a log record to be captured"
    record = handler.records[-1]
    assert record.event_type == "battery_overheat"
    assert record.safety_critical is True
    assert record.compliance_event is True
    assert record.fleet_id == "alpha-1"


def test_log_audit_event_injects_metadata(tmp_path):
    """Audit helper should capture user, resource, and outcome metadata."""

    setup_logging("INFO", log_directory=tmp_path)
    logger = get_logger("app")
    handler = _ListHandler()
    logger.addHandler(handler)

    try:
        log_audit_event(
            logger,
            action="update",
            resource_type="drone",
            resource_id="dr-1",
            user_id="user-99",
            success=False,
        )
    finally:
        logger.removeHandler(handler)

    assert handler.records, "Expected a log record to be captured"
    record = handler.records[-1]
    assert record.audit_event is True
    assert record.compliance_event is True
    assert record.action == "update"
    assert record.resource_type == "drone"
    assert record.resource_id == "dr-1"
    assert record.user_id == "user-99"
    assert record.success is False