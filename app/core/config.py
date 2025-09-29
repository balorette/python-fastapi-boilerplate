"""Application configuration settings."""

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings bundled with convenience accessors."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Core metadata
    APP_NAME: str = Field(default="MyAPI", description="Human friendly app name")
    PROJECT_NAME: str = Field(default="API", description="Project name")
    PROJECT_VERSION: str = Field(default="0.1.0", description="Project version")
    SERVICE_NAME: str = Field(default="my-api", description="Structured logging service identifier")

    # Environment & runtime flags
    ENVIRONMENT: str = Field(default="development", description="Deployment environment name")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    INIT_DB: bool = Field(default=False, description="Initialize database on startup")

    # Logging & observability
    LOG_LEVEL: str = Field(default="INFO", description="Base log level")
    LOG_DIRECTORY: str = Field(default="logs", description="Directory for rotated log files")
    AUDIT_LOG_ENABLED: bool = Field(default=True, description="Emit audit/compliance logs")
    SAFETY_CHECKS_ENABLED: bool = Field(default=True, description="Enable safety guardrails")
    PROMETHEUS_METRICS_ENABLED: bool = Field(default=False, description="Expose Prometheus metrics endpoint")

    # API configuration
    API_V1_STR: str = Field(default="/api/v1", description="Versioned API prefix")

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT - MUST be changed in production!",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration time")
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = Field(default=24, description="Password reset token expiration time in hours")

    # JWT / OAuth2 configuration
    JWT_ISSUER: str = Field(
        default="https://your-api.com",
        description="JWT issuer claim (iss) for OAuth2 compliance",
    )
    JWT_AUDIENCE: str = Field(
        default="your-frontend-app",
        description="JWT audience claim (aud) for OAuth2 compliance",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, description="Refresh token expiration in days")

    # OAuth providers - Google
    GOOGLE_OAUTH_ENABLED: bool = Field(default=False, description="Use Google OAuth")
    GOOGLE_CLIENT_ID: str = Field(default="your-google-client-id", description="Google Client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="your-google-client-secret", description="Google Client Secret")
    GOOGLE_REDIRECT_URI: str = Field(default="your-google-redirect-uri", description="Google Redirect URI")

    # Database
    DATABASE_URL: PostgresDsn | str | None = Field(default="sqlite:///./app.db", description="Database URL")
    DATABASE_URL_ASYNC: PostgresDsn | str | None = Field(default="sqlite+aiosqlite:///./app.db", description="Async database URL")
    DATABASE_TYPE: str = Field(default="sqlite", description="Database type")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    # CORS / security headers
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = Field(default_factory=list, description="CORS origins")
    CORS_ALLOW_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    TRUSTED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])

    # Middleware tuning
    PERFORMANCE_SLOW_REQUEST_THRESHOLD_MS: float = Field(default=1000.0, description="Slow request threshold in milliseconds")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, description="Requests per minute per client")
    RATE_LIMIT_EXEMPT_PATHS: tuple[str, ...] = Field(
        default=(
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/authorize",
            "/api/v1/auth/token",
            "/api/v1/auth/refresh",
        ),
        description="Paths exempt from rate limiting",
    )

    # Server configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of workers")

    # General rate limiting switch retained for backwards compatibility
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per minute")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: str | list[str]) -> list[str] | str:
        """Assemble CORS origins from environment variable."""

        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, (list, str)):
            return value
        raise ValueError(value)

    @property
    def app_version(self) -> str:
        """Return the application version string."""

        return self.PROJECT_VERSION

    @property
    def environment(self) -> str:
        """Expose environment name in snake_case style consumed by health endpoints."""

        return self.ENVIRONMENT

    @property
    def debug(self) -> bool:
        """Expose debug flag for downstream checks."""

        return self.DEBUG

    @property
    def audit_log_enabled(self) -> bool:
        """Expose audit logging flag with lower-case accessor."""

        return self.AUDIT_LOG_ENABLED

    @property
    def safety_checks_enabled(self) -> bool:
        """Expose safety check flag with lower-case accessor."""

        return self.SAFETY_CHECKS_ENABLED

    @property
    def prometheus_metrics_enabled(self) -> bool:
        """Expose Prometheus toggle expected by health endpoints."""

        return self.PROMETHEUS_METRICS_ENABLED

    @property
    def log_directory(self) -> str:
        """Directory used for structured log handlers."""

        return self.LOG_DIRECTORY

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""

        if self.DATABASE_URL:
            return str(self.DATABASE_URL).startswith("sqlite")
        return True

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database."""

        if self.DATABASE_URL:
            return str(self.DATABASE_URL).startswith("postgresql")
        return False


# Create settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""

    return settings
