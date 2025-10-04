"""Main FastAPI application module."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.middleware import (
    PerformanceMonitoringMiddleware,
    RateLimitingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.routes.metrics import attach_metrics_endpoint
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import init_database
from app.core.error_handlers import register_error_handlers
from app.core.logging import get_logger, setup_logging


logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    setup_logging(settings.LOG_LEVEL)
    logger.info("Application starting", extra={"environment": settings.environment})

    if settings.SECRET_KEY == "your-secret-key-change-this-in-production":
        logger.warning(
            "Default SECRET_KEY detected. Override the value before running in production.",
            extra={"security": "secret_key"},
        )

    if settings.INIT_DB:
        logger.info("Initializing database on startup")
        await init_database()

    yield

    logger.info(
        "Application shutting down", extra={"environment": settings.environment}
    )


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="FastAPI REST API",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Add session middleware for OAuth CSRF protection
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        expose_headers=[
            settings.REQUEST_ID_HEADER_NAME,
            settings.PROCESS_TIME_HEADER_NAME,
        ],
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

    if settings.SECURITY_HEADERS_ENABLED:
        app.add_middleware(
            SecurityHeadersMiddleware,
            enable_csp=settings.SECURITY_CSP_ENABLED,
        )

    if settings.PERFORMANCE_MONITORING_ENABLED:
        app.add_middleware(
            PerformanceMonitoringMiddleware,
            slow_request_threshold_ms=settings.PERFORMANCE_SLOW_REQUEST_THRESHOLD_MS,
        )

    if settings.REQUEST_LOGGING_ENABLED:
        app.add_middleware(
            RequestLoggingMiddleware,
            correlation_header_name=settings.REQUEST_ID_HEADER_NAME,
            process_time_header_name=settings.PROCESS_TIME_HEADER_NAME,
        )

    if settings.RATE_LIMIT_ENABLED:
        requests_per_minute = (
            settings.RATE_LIMIT_REQUESTS_PER_MINUTE or settings.RATE_LIMIT_REQUESTS
        )
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=requests_per_minute,
            exempt_paths=settings.RATE_LIMIT_EXEMPT_PATHS,
        )

    # Include routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    if settings.prometheus_metrics_enabled:
        attach_metrics_endpoint(app)

    # Register error handlers
    register_error_handlers(app)

    return app


app = create_application()


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "Welcome to the API",
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""

    logger.info("Health check invoked", extra={"route": "health"})
    return {"status": "healthy"}
