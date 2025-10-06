"""Prometheus metrics endpoint wiring."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, FastAPI, Response

logger = logging.getLogger("app.metrics")


def attach_metrics_endpoint(app: FastAPI, *, registry: Any | None = None) -> None:
    """Attach the Prometheus metrics endpoint to the provided FastAPI app."""

    try:
        from prometheus_client import (  # type: ignore[import-not-found]
            CONTENT_TYPE_LATEST,
            REGISTRY,
            CollectorRegistry,
            generate_latest,
        )
    except ImportError:  # pragma: no cover - optional dependency guard
        logger.warning(
            "Prometheus metrics requested but prometheus_client is not installed",
        )
        return

    active_registry: CollectorRegistry = registry or REGISTRY
    router = APIRouter()

    @router.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        payload = generate_latest(active_registry)
        return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

    app.include_router(router)
    logger.info(
        "Prometheus metrics endpoint enabled",
        extra={"route": "/metrics", "registry": type(active_registry).__name__},
    )
