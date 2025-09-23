"""Test configuration and fixtures."""

import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db, get_async_db
from app.api.dependencies import get_user_service
from app.services.user import UserService
from main import app

# Test database URLs
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_async.db"

# Sync engine for setup/teardown
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # Disable echo for tests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine for testing
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    echo=False
)
AsyncTestingSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


async def override_get_async_db():
    """Override async database dependency for testing."""
    async with AsyncTestingSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def override_get_user_service():
    """Override user service dependency for testing."""
    async with AsyncTestingSessionLocal() as session:
        try:
            yield UserService(session)
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Create test client."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing."""
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}