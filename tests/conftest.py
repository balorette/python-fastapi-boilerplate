"""Test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.core.database import get_async_db
from app.api.dependencies import get_user_service
from app.services.user import UserService
from main import app

# Test database URL (using SQLite for testing)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False  # Disable echo for tests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class MockAsyncSession:
    """Mock async session that wraps a sync session."""
    
    def __init__(self, sync_session):
        self._session = sync_session
        
    async def execute(self, stmt):
        return self._session.execute(stmt)
    
    async def commit(self):
        return self._session.commit()
    
    async def rollback(self):
        return self._session.rollback()
        
    async def close(self):
        return self._session.close()
        
    def add(self, instance):
        return self._session.add(instance)
        
    async def refresh(self, instance):
        return self._session.refresh(instance)
    
    async def delete(self, instance):
        """Add missing delete method."""
        return self._session.delete(instance)
    
    def scalar_one_or_none(self):
        """Mock method for scalar results."""
        return None


def override_get_async_db():
    """Override async database dependency with sync session for testing."""
    try:
        sync_session = TestingSessionLocal()
        mock_session = MockAsyncSession(sync_session)
        yield mock_session
    finally:
        sync_session.close()


def override_get_user_service():
    """Override user service dependency for testing."""
    try:
        sync_session = TestingSessionLocal()
        mock_session = MockAsyncSession(sync_session)
        yield UserService(mock_session)
    finally:
        sync_session.close()


@pytest.fixture
def client():
    """Create test client."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_user_service] = override_get_user_service
    
    with TestClient(app) as test_client:
        yield test_client
    
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
async def async_session():
    """Create async session fixture for tests that need it."""
    sync_session = TestingSessionLocal()
    mock_session = MockAsyncSession(sync_session)
    try:
        yield mock_session
    finally:
        sync_session.close()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing."""
    # Since auth routes are disabled, create a test token directly
    from app.core.security import create_access_token
    token_data = {"sub": "1", "email": "test@example.com"}
    token = create_access_token(token_data)
    return {"Authorization": f"Bearer {token}"}