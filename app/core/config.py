"""Application configuration settings."""

from typing import List, Optional, Union

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=True, description="Debug mode")

    # API Configuration
    API_V1_STR: str = Field(default="/api/v1", description="API v1 prefix")
    PROJECT_NAME: str = Field(default="API", description="Project name")
    PROJECT_VERSION: str = Field(default="0.1.0", description="Project version")
    INIT_DB: bool = Field(default=False, description="Initialize database on startup")

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT - MUST be changed in production!",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time"
    )

    # Database
    DATABASE_URL: Optional[Union[PostgresDsn, str]] = Field(
        default="sqlite:///./app.db", description="Database URL"
    )
    DATABASE_URL_ASYNC: Optional[Union[PostgresDsn, str]] = Field(
        default="sqlite+aiosqlite:///./app.db", description="Async database URL"
    )
    DATABASE_TYPE: str = Field(default="sqlite", description="Database type")

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

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=[], description="CORS origins"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Assemble CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of workers")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per minute")


# Create settings instance
settings = Settings()
