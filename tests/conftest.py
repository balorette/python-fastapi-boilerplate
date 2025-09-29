"""Test configuration and fixtures with SQLite integration."""

import asyncio
import os
import tempfile
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db_session, get_user_service
from app.core.database import get_async_db
from app.core.security import get_password_hash
from app.models.base import Base
from app.models.user import User
from app.services.user import UserService
from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an isolated SQLite database for each test case."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database_url = f"sqlite+aiosqlite:///{path}"

    engine = create_async_engine(
        database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            try:
                yield session
            finally:
                if session.in_transaction():
                    await session.rollback()
        await engine.dispose()
    finally:
        if os.path.exists(path):
            os.remove(path)


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
async def client_with_db(async_db_session: AsyncSession):
    """Create test client with database integration."""
    # Override dependencies
    app.dependency_overrides[get_async_db] = lambda: async_db_session
    app.dependency_overrides[get_user_service] = lambda: UserService(async_db_session)
    
    async def _override_get_db_session():
        return async_db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create simple test client for basic API tests."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def sample_user(async_db_session: AsyncSession):
    """Create a test user in the database."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    user_data = User(
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com", 
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
async def admin_user(async_db_session: AsyncSession):
    """Create an admin user in the database."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    admin_data = User(
        username=f"admin_{unique_id}",
        email=f"admin_{unique_id}@example.com",
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
async def auth_headers(client_with_db, admin_user):
    """Get authentication headers using OAuth2 login."""
    # Use the dynamic admin user's email
    admin_email = admin_user.email
    
    # First try the local login endpoint
    login_response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": admin_email,
            "password": "AdminPass123!",
            "grant_type": "password"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # If OAuth login doesn't work, try the basic auth login
    login_response = client_with_db.post(
        "/api/v1/auth/login",
        data={
            "username": admin_email,
            "password": "AdminPass123!"
        }
    )
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    # If both fail, raise an error with debugging info
    raise Exception(f"Login failed for {admin_email}. OAuth response: {login_response.status_code} - {login_response.text}")


# Backward compatibility fixtures
@pytest.fixture
async def async_session(async_db_session: AsyncSession):
    """Legacy fixture name for backward compatibility."""
    return async_db_session


@pytest.fixture
async def sample_user_in_db(sample_user: User):
    """Legacy fixture name for backward compatibility."""
    return sample_user


@pytest.fixture
async def admin_user_in_db(admin_user: User):
    """Legacy fixture name for backward compatibility."""
    return admin_user


@pytest.fixture
async def client_with_real_db(client_with_db):
    """Legacy fixture name for backward compatibility."""
    return client_with_db
