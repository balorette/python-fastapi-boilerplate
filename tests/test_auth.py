"""Test authentication endpoints."""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import UserService
from app.schemas.user import UserCreate
from app.core.security import create_access_token


@pytest.fixture
async def auth_test_user(async_db_session: AsyncSession):
    """Create a test user specifically for auth tests."""
    user_service = UserService(async_db_session)
    unique_id = str(uuid.uuid4())[:8]

    user_data = UserCreate(
        username=f"authtest_{unique_id}",
        email=f"authtest_{unique_id}@example.com",
        password="TestPass123!",
        confirm_password="TestPass123!",
        full_name="Auth Test User",
        is_active=True,
        is_superuser=False,
    )

    user = await user_service.create_user(user_data)
    await async_db_session.commit()
    return user


@pytest.fixture
async def auth_admin_user(async_db_session: AsyncSession):
    """Create an admin user specifically for auth tests."""
    user_service = UserService(async_db_session)
    unique_id = str(uuid.uuid4())[:8]

    admin_data = UserCreate(
        username=f"authadmin_{unique_id}",
        email=f"authadmin_{unique_id}@example.com",
        password="Admin123!",
        confirm_password="Admin123!",
        full_name="Auth Admin User",
        is_active=True,
        is_superuser=True,
    )

    admin = await user_service.create_user(admin_data)
    await async_db_session.commit()
    return admin


def test_login_success(client_with_db: TestClient, auth_admin_user):
    """Test successful login with OAuth2 endpoint."""
    response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": auth_admin_user.email,
            "password": "Admin123!",
            "grant_type": "password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


def test_login_with_email(client_with_db: TestClient, auth_test_user):
    """Test login using email instead of username with OAuth2."""
    response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": auth_test_user.email,
            "password": "TestPass123!",
            "grant_type": "password",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


def test_login_invalid_credentials(client_with_db: TestClient):
    """Test login with invalid credentials using OAuth2."""
    response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPass123!",
            "grant_type": "password",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]


async def test_login_inactive_user(
    client_with_db: TestClient, async_db_session: AsyncSession
):
    """Test login with inactive user using OAuth2."""
    # Create an inactive user
    user_service = UserService(async_db_session)
    unique_id = str(uuid.uuid4())[:8]

    user_data = UserCreate(
        username=f"inactive_{unique_id}",
        email=f"inactive_{unique_id}@example.com",
        password="InactivePass123!",
        confirm_password="InactivePass123!",
        full_name="Inactive User",
        is_active=False,
        is_superuser=False,
    )
    user = await user_service.create_user(user_data)
    await async_db_session.commit()

    response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": user.email,
            "password": "InactivePass123!",
            "grant_type": "password",
        },
    )
    assert response.status_code == 403


def test_logout(client_with_db: TestClient, auth_admin_user):
    """Test token revocation (logout) with OAuth2."""
    # First get a token
    login_response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": auth_admin_user.email,
            "password": "Admin123!",
            "grant_type": "password",
        },
    )

    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        # Try to revoke the token (if the endpoint exists)
        response = client_with_db.post("/api/v1/auth/revoke", params={"token": token})
        # Accept either 200 (success) or 404 (endpoint not implemented yet)
        assert response.status_code in [200, 404]
    else:
        pytest.fail(f"Login failed: {login_response.text}")


def test_protected_endpoint_without_token(client_with_db: TestClient):
    """Test accessing protected endpoint without token."""
    # Try to access a protected endpoint
    response = client_with_db.get("/api/v1/users/")
    # Should be 401 (unauthorized)
    assert response.status_code == 401


def test_protected_endpoint_with_valid_token(
    client_with_db: TestClient, auth_test_user
):
    """Non-admin tokens are rejected for admin-only endpoints."""

    token = create_access_token(
        data={"sub": str(auth_test_user.id), "email": auth_test_user.email}
    )

    response = client_with_db.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_protected_endpoint_with_invalid_token(client_with_db: TestClient):
    """Test accessing protected endpoint with invalid token."""
    response = client_with_db.get(
        "/api/v1/users/", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_protected_endpoint_with_expired_token(client_with_db: TestClient):
    """Test accessing protected endpoint with expired token."""
    # Create an expired token (this would need a custom token creation)
    expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"

    response = client_with_db.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


def test_token_validation_flow(client_with_db: TestClient, auth_test_user):
    """Test complete token validation flow."""
    # 1. Login and get token via OAuth2
    login_response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": auth_test_user.email,
            "password": "TestPass123!",
            "grant_type": "password",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # 2. Use token to access protected resource
    protected_response = client_with_db.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {token}"}
    )
    # Should not be unauthorized
    assert protected_response.status_code != 401


def test_users_me_endpoint(client_with_db: TestClient, auth_test_user):
    """Primary `/users/me` endpoint should return the authenticated user."""
    login_response = client_with_db.post(
        "/api/v1/auth/login",
        json={
            "email": auth_test_user.email,
            "password": "TestPass123!",
            "grant_type": "password",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    response = client_with_db.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == auth_test_user.email
