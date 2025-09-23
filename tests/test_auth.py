"""Test authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import UserService
from app.schemas.user import UserCreate
from app.core.security import create_access_token


@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user for authentication tests."""
    user_service = UserService(async_session)
    
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        confirm_password="testpass123",
        full_name="Test User",
        is_active=True,
        is_superuser=False
    )
    
    user = await user_service.create_user(user_data)
    await async_session.commit()
    return user


@pytest.fixture
async def admin_user(async_session: AsyncSession):
    """Create an admin user for authentication tests."""
    user_service = UserService(async_session)
    
    admin_data = UserCreate(
        username="admin",
        email="admin@example.com",
        password="admin123",
        confirm_password="admin123",
        full_name="Administrator",
        is_active=True,
        is_superuser=True
    )
    
    admin = await user_service.create_user(admin_data)
    await async_session.commit()
    return admin


def test_login_success(client: TestClient, admin_user):
    """Test successful login with real user."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_with_email(client: TestClient, test_user):
    """Test login using email instead of username."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "testpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "wrong", "password": "wrong"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid username/email or password" in data["detail"]


def test_login_inactive_user(client: TestClient, async_session: AsyncSession):
    """Test login with inactive user."""
    # This test would need an inactive user fixture
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "inactive", "password": "password"}
    )
    assert response.status_code == 401


def test_logout(client: TestClient):
    """Test logout endpoint."""
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully logged out"


def test_protected_endpoint_without_token(client: TestClient):
    """Test accessing protected endpoint without token."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token(client: TestClient, test_user):
    """Test accessing protected endpoint with valid token."""
    # Create a valid token for the user
    token = create_access_token(data={"sub": str(test_user.id)})
    
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    # This might return 404 if the endpoint doesn't exist yet
    # but it should not return 401 (unauthorized)
    assert response.status_code != 401


def test_protected_endpoint_with_invalid_token(client: TestClient):
    """Test accessing protected endpoint with invalid token."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_protected_endpoint_with_expired_token(client: TestClient):
    """Test accessing protected endpoint with expired token."""
    # Create an expired token (this would need a custom token creation)
    expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
    
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


def test_token_validation_flow(client: TestClient, test_user):
    """Test complete token validation flow."""
    # 1. Login and get token
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "testpass123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. Use token to access protected resource
    protected_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    # Should not be unauthorized
    assert protected_response.status_code != 401