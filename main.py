"""Main FastAPI application module."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.error_handlers import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    setup_logging()
    
    # Security warning for default secret key
    if settings.SECRET_KEY == "your-secret-key-change-this-in-production":
        print(
            "⚠️  WARNING: Using default SECRET_KEY! "
            "This is INSECURE for production use. "
            "Please set a secure SECRET_KEY environment variable."
        )
    
    yield
    # Shutdown
    pass


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

    # Set all CORS enabled origins
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add trusted host middleware in production
    if settings.ENVIRONMENT == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # Include routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
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
    return {"status": "healthy"}