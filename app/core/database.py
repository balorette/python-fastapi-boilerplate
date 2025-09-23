"""Database configuration and session management."""

from typing import Any, AsyncGenerator, Dict
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.base import Base

# Ensure SQLite directory exists
if settings.is_sqlite:
    db_path = str(settings.DATABASE_URL).replace("sqlite:///", "")
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

# Configure engine settings based on database type
engine_kwargs: Dict[str, Any] = {"echo": settings.DEBUG}
async_engine_kwargs: Dict[str, Any] = {"echo": settings.DEBUG}

if settings.is_sqlite:
    # SQLite specific settings with connection pooling
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
        "pool_pre_ping": True,
        "pool_recycle": -1,
    })
    async_engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
elif settings.is_postgresql:
    # PostgreSQL specific settings with connection pooling
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # 1 hour
        "pool_size": 10,
        "max_overflow": 20,
    })
    async_engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    })

# Enhanced engines with better error handling
try:
    engine = create_engine(str(settings.DATABASE_URL), **engine_kwargs)
    async_engine = create_async_engine(str(settings.DATABASE_URL_ASYNC), **async_engine_kwargs)
except Exception as e:
    raise RuntimeError(f"Failed to create database engine: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

def get_db():
    """Get synchronous database session with proper error handling."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session with proper error handling."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


@asynccontextmanager
async def get_async_db_context():
    """Context manager for async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e

async def create_tables():
    """Create all database tables."""
    if settings.is_sqlite:
        # For SQLite, create tables synchronously first
        Base.metadata.create_all(bind=engine)
    else:
        # For PostgreSQL, create tables asynchronously
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def init_database():
    """Initialize database with tables and any required data."""
    try:
        await create_tables()
        print(f"✅ Database initialized successfully using {settings.DATABASE_TYPE}")
        if settings.is_sqlite:
            db_path = str(settings.DATABASE_URL).replace("sqlite:///", "")
            print(f"📁 SQLite database created at: {db_path}")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        raise

# Database health check
async def check_database_health() -> bool:
    """Check if database is accessible."""
    try:
        async with get_async_db_context() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False