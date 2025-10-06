"""Reusable middleware components for the FastAPI boilerplate."""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable

import anyio
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach correlation IDs, timing metadata, and structured logs to requests."""

    def __init__(
        self,
        app,
        *,
        correlation_header_name: str = "X-Correlation-ID",
        process_time_header_name: str = "X-Process-Time",
    ) -> None:
        super().__init__(app)
        self._correlation_header_name = correlation_header_name
        self._process_time_header_name = process_time_header_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Log incoming requests, record execution time, and enrich responses."""

        correlation_id = str(uuid.uuid4())
        request.state.request_id = correlation_id
        request.state.correlation_id = correlation_id

        start_time = time.perf_counter()
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "request_id": correlation_id,
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
                    "request_id": correlation_id,
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
                "request_id": correlation_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time_ms": round(process_time_ms, 2),
            },
        )

        if self._correlation_header_name:
            response.headers[self._correlation_header_name] = correlation_id
        if self._process_time_header_name:
            response.headers[self._process_time_header_name] = f"{process_time_ms:.2f}"
        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Capture metrics and alert on requests that exceed the configured threshold."""

    def __init__(self, app, *, slow_request_threshold_ms: float = 1000.0) -> None:
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
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
    """Attach baseline security headers to every HTTP response.

    Implements OWASP security best practices including CSP, XSS protection,
    clickjacking prevention, and secure content type handling.
    """

    DOCS_PATH_SUFFIXES = {"/docs", "/redoc", "/docs/oauth2-redirect"}
    DOCS_SCRIPT_SOURCES = [
        "'unsafe-inline'",
        "'unsafe-eval'",
        "https://cdn.jsdelivr.net",
    ]
    DOCS_STYLE_SOURCES = ["'unsafe-inline'", "https://cdn.jsdelivr.net"]

    def __init__(self, app, *, enable_csp: bool = True) -> None:
        super().__init__(app)
        self._enable_csp = enable_csp

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Ensure security best-practice headers are present on responses."""

        response = await call_next(request)

        # Prevent MIME-sniffing attacks
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Prevent clickjacking attacks
        response.headers.setdefault("X-Frame-Options", "DENY")

        # Enable XSS protection (legacy browsers)
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        # Control referrer information
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )

        # Content Security Policy for production hardening
        if self._enable_csp:
            response.headers.setdefault(
                "Content-Security-Policy",
                self._build_csp_header(request),
            )

        # Control Adobe/Flash cross-domain policy file usage
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")

        return response

    def _build_csp_header(self, request: Request) -> str:
        """Construct a CSP value, relaxing rules for FastAPI documentation assets."""

        script_sources = ["'self'"]
        style_sources = ["'self'"]

        # FastAPI's Swagger UI and ReDoc pull assets from jsDelivr.
        if self._is_docs_route(request.url.path):
            script_sources.extend(self.DOCS_SCRIPT_SOURCES)
            style_sources.extend(self.DOCS_STYLE_SOURCES)

        directives = [
            "default-src 'self'",
            f"script-src {' '.join(script_sources)}",
            f"style-src {' '.join(style_sources)}",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
        ]

        return "; ".join(directives)

    def _is_docs_route(self, path: str) -> bool:
        """Return True when the request targets Swagger UI or ReDoc HTML."""

        normalized = path.rstrip("/") or "/"
        return any(normalized.endswith(suffix) for suffix in self.DOCS_PATH_SUFFIXES)


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
        # Use an anyio lock so it binds to the currently running loop/backend.
        # This avoids "Event loop is closed" errors when the ASGI app is driven
        # by short-lived event loops (e.g. pytest's TestClient per test case).
        self._lock = anyio.Lock()
        self._requests: dict[str, dict[int, int]] = defaultdict(dict)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
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
