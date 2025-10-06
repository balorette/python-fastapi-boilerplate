"""Enhanced database configuration with improved async SQLAlchemy patterns."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

import app.models  # noqa: F401  # Ensure models are registered with SQLAlchemy metadata
from app.core.authz import ensure_default_roles
from app.core.config import settings
from app.models.base import Base

# Configure logging for database operations
logger = logging.getLogger(__name__)


# Enhanced engine configuration with better asyncpg compatibility
def get_engine_config() -> tuple[dict[str, Any], dict[str, Any]]:
    """Get optimized engine configuration for different database types."""

    base_engine_kwargs = {
        "echo": settings.DEBUG,
        "future": True,  # Use SQLAlchemy 2.0 style
    }

    base_async_kwargs = {
        "echo": settings.DEBUG,
        "future": True,
    }

    if settings.is_sqlite:
        # Ensure SQLite directory exists
        db_path = str(settings.DATABASE_URL).replace("sqlite:///", "")
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # SQLite-specific configuration
        sqlite_config = {
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20,  # Connection timeout
            },
            "poolclass": StaticPool,
            "pool_pre_ping": True,
            "pool_recycle": -1,
        }
        return (
            {**base_engine_kwargs, **sqlite_config},
            {**base_async_kwargs, **sqlite_config},
        )

    elif settings.is_postgresql:
        # PostgreSQL synchronous engine configuration
        sync_pg_config = {
            "poolclass": QueuePool,
            "pool_size": 5,  # Conservative pool size
            "max_overflow": 10,  # Reasonable overflow
            "pool_timeout": 30,  # Connection acquisition timeout
            "pool_recycle": 1800,  # 30 minutes (better for asyncpg)
            "pool_pre_ping": True,  # Validate connections
            "pool_reset_on_return": "commit",  # Clean state on return
        }

        # PostgreSQL async engine configuration (different from sync)
        async_pg_config = {
            # Note: async engines use their own connection pooling
            "pool_size": 5,  # Conservative pool size
            "max_overflow": 10,  # Reasonable overflow
            "pool_timeout": 30,  # Connection acquisition timeout
            "pool_recycle": 1800,  # 30 minutes (better for asyncpg)
            "pool_pre_ping": True,  # Validate connections
        }

        # asyncpg-specific connect args
        async_connect_args = {
            "server_settings": {
                "application_name": "fastapi_app",
                "jit": "off",  # Disable JIT for better connection stability
            },
            "command_timeout": 60,  # Command timeout
        }

        return (
            {**base_engine_kwargs, **sync_pg_config},
            {
                **base_async_kwargs,
                **async_pg_config,
                "connect_args": async_connect_args,
            },
        )

    else:
        return base_engine_kwargs, base_async_kwargs


# Create engines with enhanced configuration
engine_kwargs, async_engine_kwargs = get_engine_config()

try:
    # Sync engine for migrations and admin operations
    engine = create_engine(str(settings.DATABASE_URL), **engine_kwargs)

    # Async engine with proper asyncpg configuration
    async_engine = create_async_engine(
        str(settings.DATABASE_URL_ASYNC), **async_engine_kwargs
    )

    logger.info(f"Database engines created successfully for {settings.DATABASE_TYPE}")

except Exception as exc:
    logger.error(f"Failed to create database engines: {exc}")
    raise RuntimeError(f"Database engine creation failed: {exc}") from exc

# Configure session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Prevent automatic flushing
)


# Add event listeners for better connection management
@event.listens_for(async_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configure SQLite pragmas for better performance and reliability."""
    if settings.is_sqlite:
        cursor = dbapi_connection.cursor()
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        # Set busy timeout
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


@event.listens_for(async_engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout events."""
    logger.debug("Connection checked out from pool")


@event.listens_for(async_engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin events."""
    logger.debug("Connection checked in to pool")


# Enhanced session dependencies with better error handling
def get_db():
    """Get synchronous database session with enhanced error handling."""
    db = SessionLocal()
    try:
        yield db
    except (DisconnectionError, OperationalError) as e:
        logger.error(f"Database connection error in sync session: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in sync session: {e}")
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session with enhanced error handling and retry logic."""
    session = None
    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            session = AsyncSessionLocal()

            # Test connection before yielding
            await session.execute(text("SELECT 1"))

            yield session
            await session.commit()
            break

        except (DisconnectionError, OperationalError) as e:
            logger.warning(
                f"Database connection error (attempt {retry_count + 1}): {e}"
            )
            if session:
                await session.rollback()
                await session.close()
                session = None

            retry_count += 1
            if retry_count >= max_retries:
                logger.error(
                    f"Failed to establish database connection after {max_retries} attempts"
                )
                raise

            # Wait before retry with exponential backoff
            await asyncio.sleep(2**retry_count)

        except Exception as exc:
            logger.error(f"Unexpected error in async session: {exc}")
            if session:
                await session.rollback()
                await session.close()
            raise
        finally:
            if session and retry_count < max_retries:
                await session.close()


@asynccontextmanager
async def get_async_db_context():
    """Enhanced context manager for async database sessions."""
    session = None
    try:
        session = AsyncSessionLocal()

        # Validate connection
        await session.execute(text("SELECT 1"))

        yield session
        await session.commit()

    except (DisconnectionError, OperationalError) as exc:
        logger.error(f"Database connection error in context manager: {exc}")
        if session:
            await session.rollback()
        raise
    except Exception as exc:
        logger.error(f"Error in database context manager: {exc}")
        if session:
            await session.rollback()
        raise
    finally:
        if session:
            await session.close()


# Enhanced database initialization
async def create_tables():
    """Create all database tables with proper error handling."""
    try:
        if settings.is_sqlite:
            # For SQLite, create tables synchronously to avoid event loop issues
            logger.info("Creating SQLite tables synchronously...")
            Base.metadata.create_all(bind=engine)
        else:
            # For PostgreSQL, create tables asynchronously
            logger.info("Creating PostgreSQL tables asynchronously...")
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    except Exception as exc:
        logger.error(f"Failed to create database tables: {exc}")
        raise


async def init_database():
    """Initialize database with enhanced error handling and logging."""
    try:
        logger.info(f"Initializing {settings.DATABASE_TYPE} database...")

        # Test connection first
        health = await check_database_health()
        if not health["connection_status"] == "healthy":
            raise RuntimeError("Database health check failed")

        await create_tables()

        # Seed default roles and permissions for RBAC
        async with AsyncSessionLocal() as session:
            await ensure_default_roles(session)

        logger.info(
            f"✅ Database initialized successfully using {settings.DATABASE_TYPE}"
        )

        if settings.is_sqlite:
            db_path = str(settings.DATABASE_URL).replace("sqlite:///", "")
            logger.info(f"📁 SQLite database created at: {db_path}")
        else:
            logger.info("🐘 PostgreSQL database connected")

    except Exception as exc:
        logger.error(f"❌ Failed to initialize database: {exc}")
        raise


# Enhanced health check with connection pool status
async def check_database_health() -> dict[str, Any]:
    """Enhanced database health check with detailed status."""
    health_status = {
        "database_type": settings.DATABASE_TYPE,
        "connection_status": "unknown",
        "pool_status": {},
        "error": None,
    }

    try:
        async with get_async_db_context() as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1 as health_check"))
            health_value = result.scalar()

            if health_value == 1:
                health_status["connection_status"] = "healthy"

                # Get pool status for PostgreSQL
                if settings.is_postgresql:
                    try:
                        health_status["pool_status"] = {
                            "pool_available": async_engine.pool is not None,
                            "engine_status": "connected",
                        }
                    except Exception:
                        health_status["pool_status"] = {
                            "pool_available": False,
                            "engine_status": "unknown",
                        }
            else:
                health_status["connection_status"] = "unhealthy"
                health_status["error"] = "Health check query returned unexpected result"

    except Exception as exc:
        health_status["connection_status"] = "error"
        health_status["error"] = str(exc)
        logger.error(f"Database health check failed: {exc}")

    return health_status


# Graceful shutdown function
async def close_database_connections():
    """Gracefully close all database connections and dispose engines."""
    try:
        logger.info("Closing database connections...")

        # Close async engine
        if async_engine:
            await async_engine.dispose()
            logger.info("Async engine disposed")

        # Close sync engine
        if engine:
            engine.dispose()
            logger.info("Sync engine disposed")

        logger.info("✅ Database connections closed successfully")

    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


# Connection validation utility
async def validate_connection() -> bool:
    """Validate that database connection is working properly."""
    try:
        async with get_async_db_context() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Connection validation failed: {e}")
        return False


# Export commonly used items
__all__ = [
    "engine",
    "async_engine",
    "SessionLocal",
    "AsyncSessionLocal",
    "get_db",
    "get_async_db",
    "get_async_db_context",
    "init_database",
    "check_database_health",
    "close_database_connections",
    "validate_connection",
]
