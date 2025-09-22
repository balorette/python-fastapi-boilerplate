"""Database configuration and session management."""

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Base class for models
Base = declarative_base()

# Configure engine settings based on database type
engine_kwargs = {"echo": settings.DEBUG}
async_engine_kwargs = {"echo": settings.DEBUG}

if settings.is_sqlite:
    # SQLite specific settings
    engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
    }) # type: ignore
    async_engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
    }) # type: ignore
elif settings.is_postgresql:
    # PostgreSQL specific settings
    engine_kwargs.update({
        "pool_pre_ping": True,
    })
    async_engine_kwargs.update({
        "pool_pre_ping": True,
    })

# Sync engine and session
engine = create_engine(str(settings.DATABASE_URL), **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine and session
async_engine = create_async_engine(str(settings.DATABASE_URL_ASYNC), **async_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_db():
    """Get synchronous database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get asynchronous database session."""
    async with AsyncSessionLocal() as session:
        yield session