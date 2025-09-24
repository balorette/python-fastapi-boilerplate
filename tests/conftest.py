"""Test configuration and fixtures with PostgreSQL integration."""

import pytest
import asyncio
import uuid
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.core.database import get_async_db
from app.api.dependencies import get_user_service
from app.services.user import UserService
from app.models.user import User
from app.core.security import get_password_hash
from main import app

# PostgreSQL test database configuration
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "mydbpassword"
POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = "5432"
POSTGRES_DB_BASE = "fastapi_test"

# Use a simpler approach with per-function database isolation
POSTGRES_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}"
POSTGRES_TEST_DB = f"{POSTGRES_DB_BASE}_main"
TEST_DATABASE_URL = f"{POSTGRES_URL}/{POSTGRES_TEST_DB}"
ASYNC_TEST_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_TEST_DB}"

# Create sync engine for database setup/teardown
setup_engine = create_engine(f"{POSTGRES_URL}/postgres", isolation_level="AUTOCOMMIT")

# Async engine for actual testing with smaller pool to avoid connection issues
async_test_engine = create_async_engine(
    ASYNC_TEST_DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300
)

AsyncTestingSessionLocal = async_sessionmaker(
    bind=async_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database for the session."""
    # Create the test database
    with setup_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {POSTGRES_TEST_DB}"))
        conn.execute(text(f"CREATE DATABASE {POSTGRES_TEST_DB}"))
    
    yield
    
    # Cleanup: Drop test database after all tests
    with setup_engine.connect() as conn:
        # Force disconnect any remaining connections
        conn.execute(text(f"""
            SELECT pg_terminate_backend(pid) 
            FROM pg_stat_activity 
            WHERE datname = '{POSTGRES_TEST_DB}' AND pid <> pg_backend_pid()
        """))
        conn.execute(text(f"DROP DATABASE IF EXISTS {POSTGRES_TEST_DB}"))


@pytest.fixture(scope="session")
async def setup_tables():
    """Create tables after database is created."""
    async with async_test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Dispose of all connections
    await async_test_engine.dispose()



@pytest.fixture
async def async_db_session(setup_tables) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for integration tests with transaction rollback."""
    async with AsyncTestingSessionLocal() as session:
        # Start a transaction that we can rollback to isolate tests
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Always rollback to isolate tests
            await transaction.rollback()
            await session.close()


@pytest.fixture
def override_get_async_db(async_db_session: AsyncSession):
    """Override async database dependency."""
    def _override():
        return async_db_session
    return _override


@pytest.fixture  
def override_get_user_service(async_db_session: AsyncSession):
    """Override user service dependency."""
    def _override():
        return UserService(async_db_session)
    return _override


@pytest.fixture
async def client_with_real_db(async_db_session: AsyncSession):
    """Create test client with real database integration."""
    # Override dependencies
    app.dependency_overrides[get_async_db] = lambda: async_db_session
    app.dependency_overrides[get_user_service] = lambda: UserService(async_db_session)
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create simple test client for basic API tests (legacy compatibility)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def sample_user_in_db(async_db_session: AsyncSession):
    """Create a real user in the test database."""
    user_data = User(
        username="testuser",
        email="test@example.com", 
        full_name="Test User",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        is_superuser=False
    )
    
    async_db_session.add(user_data)
    await async_db_session.commit()
    await async_db_session.refresh(user_data)
    
    return user_data


@pytest.fixture
async def admin_user_in_db(async_db_session: AsyncSession):
    """Create a real admin user in the test database."""
    admin_data = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User", 
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True
    )
    
    async_db_session.add(admin_data)
    await async_db_session.commit()
    await async_db_session.refresh(admin_data)
    
    return admin_data


@pytest.fixture
async def auth_headers(client_with_real_db, admin_user_in_db):
    """Get real authentication headers using OAuth2 login."""
    login_response = client_with_real_db.post(
        "/api/v1/oauth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPass123!",
            "grant_type": "password"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Legacy fixtures for backward compatibility with existing tests
@pytest.fixture
async def async_session(async_db_session: AsyncSession):
    """Legacy fixture name for backward compatibility."""
    return async_db_session