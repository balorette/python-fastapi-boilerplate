"""Reusable middleware components for the FastAPI boilerplate."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from typing import Callable, Iterable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("app.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach correlation IDs, timing metadata, and structured logs to requests."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Log incoming requests, record execution time, and enrich responses."""

        correlation_id = str(uuid.uuid4())
        request.state.request_id = correlation_id

        start_time = time.perf_counter()
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - defensive logging branch
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time_ms": round(process_time_ms, 2),
                    "error": str(exc),
                },
                exc_info=True,
            )
            raise

        process_time_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Request completed",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time_ms": round(process_time_ms, 2),
            },
        )

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = f"{process_time_ms:.2f}"
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Capture metrics and alert on requests that exceed the configured threshold."""

    def __init__(self, app, *, slow_request_threshold_ms: float = 1000.0) -> None:
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Log a warning whenever a request breaches the latency budget."""

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - defensive logging branch
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Failed request timing",
                extra={
                    "correlation_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "url": str(request.url),
                    "process_time_ms": round(process_time_ms, 2),
                    "error": str(exc),
                },
            )
            raise

        process_time_ms = (time.perf_counter() - start_time) * 1000
        if process_time_ms > self.slow_request_threshold_ms:
            logger.warning(
                "Slow request detected",
                extra={
                    "correlation_id": getattr(request.state, "request_id", None),
                    "method": request.method,
                    "url": str(request.url),
                    "process_time_ms": round(process_time_ms, 2),
                    "threshold_ms": self.slow_request_threshold_ms,
                    "status_code": response.status_code,
                },
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every HTTP response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Ensure security best-practice headers are present on responses."""

        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Access-Control-Expose-Headers", "X-Correlation-ID, X-Process-Time")

        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Very small in-memory rate limiter suitable for local development."""

    def __init__(
        self,
        app,
        *,
        requests_per_minute: int = 60,
        exempt_paths: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = max(1, int(requests_per_minute))
        self.exempt_paths = {path.rstrip("/") for path in (exempt_paths or [])}
        self._lock = asyncio.Lock()
        self._requests: dict[str, dict[int, int]] = defaultdict(dict)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        """Throttle clients exceeding the configured request budget."""

        if self._is_exempt(request.url.path):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = int(time.time())
        minute_bucket = current_time // 60

        async with self._lock:
            bucket_counts = self._requests[client_ip]
            # Drop old counters to prevent unbounded growth
            for bucket in list(bucket_counts):
                if bucket < minute_bucket - 1:
                    bucket_counts.pop(bucket, None)

            current_requests = bucket_counts.get(minute_bucket, 0)
            if current_requests >= self.requests_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_ip": client_ip,
                        "requests_per_minute": self.requests_per_minute,
                        "current_requests": current_requests,
                    },
                )
                retry_after = max(1, int(60 / self.requests_per_minute))
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )

            bucket_counts[minute_bucket] = current_requests + 1

        return await call_next(request)

    def _is_exempt(self, path: str) -> bool:
        normalized_path = path.rstrip("/") or "/"
        return normalized_path in self.exempt_paths