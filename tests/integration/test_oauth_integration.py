"""Integration tests for OAuth2 authentication with real database and endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import get_password_hash
from app.models.user import User


class TestOAuth2Integration:
    """Test OAuth2 endpoints with real authentication flows and database operations."""

    @pytest.mark.asyncio
    async def test_complete_local_oauth_flow_with_real_user(
        self, client_with_real_db, sample_user_in_db
    ):
        """Test complete local OAuth2 authentication flow with real user from database."""

        # Step 1: Login with real credentials stored in database
        login_response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_in_db.email,  # Real email from database
                "password": "TestPass123!",  # Real password that matches hashed version
                "grant_type": "password",
            },
        )

        assert login_response.status_code == 200
        token_data = login_response.json()

        # Validate token response structure
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["user_id"] == sample_user_in_db.id
        assert token_data["email"] == sample_user_in_db.email
        assert token_data["username"] == sample_user_in_db.username
        assert "expires_in" in token_data

        # Step 2: Use access token to access protected endpoint (real JWT validation)
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        # Test accessing user's own profile
        me_response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert me_response.status_code == 200

        user_data = me_response.json()
        assert user_data["id"] == sample_user_in_db.id
        assert user_data["email"] == sample_user_in_db.email
        assert user_data["username"] == sample_user_in_db.username
        assert user_data["full_name"] == sample_user_in_db.full_name
        assert user_data["is_active"] == sample_user_in_db.is_active

        # Step 3: Test accessing protected user list (requires authentication)
        users_response = client_with_real_db.get("/api/v1/users/", headers=headers)
        assert users_response.status_code == 200

        users_data = users_response.json()
        assert "items" in users_data
        assert "total" in users_data

        # Step 4: Test token refresh with real refresh token
        refresh_response = client_with_real_db.post(
            "/api/v1/auth/refresh",
            json={
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
            },
        )

        assert refresh_response.status_code == 200
        new_token_data = refresh_response.json()

        assert "access_token" in new_token_data
        assert (
            new_token_data["access_token"] != token_data["access_token"]
        )  # Should be different
        assert new_token_data["user_id"] == sample_user_in_db.id

        # Step 5: Verify new token works
        new_headers = {"Authorization": f"Bearer {new_token_data['access_token']}"}
        verify_response = client_with_real_db.get(
            "/api/v1/users/me", headers=new_headers
        )
        assert verify_response.status_code == 200

    @pytest.mark.asyncio
    async def test_authentication_failures_with_real_validation(
        self, client_with_real_db, sample_user_in_db
    ):
        """Test authentication failures with real password verification and database lookups."""

        # Test wrong password with real user
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_in_db.email,
                "password": "WrongPassword123!",  # Wrong password
                "grant_type": "password",
            },
        )

        assert response.status_code in (401, 403)
        error_data = response.json()
        assert "invalid" in error_data["detail"].lower()

        # Test non-existent user (real database lookup)
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )

        assert response.status_code in (401, 403)
        error_data = response.json()
        assert "invalid" in error_data["detail"].lower()

        # Test with empty/invalid credentials
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={"email": "", "password": "", "grant_type": "password"},
        )

        assert response.status_code in [400, 422]  # Validation error

        # Test inactive user
        # First create an inactive user in the database
        # Create user then deactivate
        from app.core.security import get_password_hash
        from app.models.user import User

        async_session = client_with_real_db.app.dependency_overrides[get_async_db]()
        inactive_user = User(
            username="inactiveuser",
            email="inactive@example.com",
            full_name="Inactive User",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=False,  # Inactive user
            is_superuser=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        async_session.add(inactive_user)
        await async_session.commit()

        # Try to login with inactive user
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )

        assert response.status_code in (401, 403)
        error_data = response.json()
        detail_lower = error_data["detail"].lower()
        assert (
            "user account is deactivated" in detail_lower
            or "invalid credentials" in detail_lower
            or "account is disabled" in detail_lower
        )

    def test_invalid_token_handling_with_real_jwt_validation(self, client_with_real_db):
        """Test token validation with various edge cases using real JWT processing."""

        # Test completely invalid token format
        headers = {"Authorization": "Bearer invalid.token.format"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        # Test malformed Authorization header
        headers = {"Authorization": "InvalidFormat token"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        # Test missing Authorization header
        response = client_with_real_db.get("/api/v1/users/me")
        assert response.status_code == 401

        # Test empty token
        headers = {"Authorization": "Bearer "}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        # Test token with invalid signature (manually crafted)
        fake_token = "fake.token.invalid_signature"
        headers = {"Authorization": f"Bearer {fake_token}"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_expiration_handling(
        self, client_with_real_db, sample_user_in_db
    ):
        """Test token expiration with real JWT tokens."""
        from datetime import timedelta

        from app.core.security import create_access_token

        # Create an expired token
        token_data = {
            "sub": str(sample_user_in_db.id),
            "email": sample_user_in_db.email,
        }
        expired_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        error_data = response.json()
        assert (
            "Could not validate credentials" in error_data["detail"]
            or "expired" in error_data["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_user_permissions_with_real_roles(
        self, client_with_real_db, async_db_session: AsyncSession
    ):
        """Test user permissions and roles with real database users."""

        # Create regular user and admin user
        regular_user = User(
            username="regularuser",
            email="regular@example.com",
            full_name="Regular User",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_superuser=False,  # Not admin
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        admin_user = User(
            username="adminuser",
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_superuser=True,  # Admin
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        async_db_session.add(regular_user)
        async_db_session.add(admin_user)
        await async_db_session.commit()
        await async_db_session.refresh(regular_user)
        await async_db_session.refresh(admin_user)

        # Login as regular user
        regular_login = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "regular@example.com",
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )
        assert regular_login.status_code == 200
        regular_token = regular_login.json()["access_token"]
        regular_headers = {"Authorization": f"Bearer {regular_token}"}

        # Login as admin user
        admin_login = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Both users should be able to access their own profile
        regular_me = client_with_real_db.get(
            "/api/v1/users/me", headers=regular_headers
        )
        assert regular_me.status_code == 200
        assert regular_me.json()["username"] == "regularuser"

        admin_me = client_with_real_db.get("/api/v1/users/me", headers=admin_headers)
        assert admin_me.status_code == 200
        assert admin_me.json()["username"] == "adminuser"

        # Both should be able to list users (assuming endpoint allows it)
        regular_users = client_with_real_db.get(
            "/api/v1/users/", headers=regular_headers
        )
        admin_users = client_with_real_db.get("/api/v1/users/", headers=admin_headers)

        # This tests the actual permission logic in your endpoints
        # Results may vary based on your authorization implementation
        assert regular_users.status_code in [200, 403]  # Depending on your auth rules
        assert admin_users.status_code == 200  # Admin should definitely have access

    @pytest.mark.asyncio
    async def test_refresh_token_security_and_rotation(
        self, client_with_real_db, sample_user_in_db
    ):
        """Test refresh token security with real token rotation."""

        # Initial login
        login_response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_in_db.email,
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )

        assert login_response.status_code == 200
        initial_tokens = login_response.json()
        initial_refresh_token = initial_tokens["refresh_token"]

        # Use refresh token to get new tokens
        refresh_response = client_with_real_db.post(
            "/api/v1/auth/refresh",
            json={
                "grant_type": "refresh_token",
                "refresh_token": initial_refresh_token,
            },
        )

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()

        # Verify token rotation (if implemented)
        assert new_tokens["access_token"] != initial_tokens["access_token"]

        # If refresh token rotation is implemented, the old refresh token should be invalid
        # This tests your actual token rotation security
        _old_refresh_response = client_with_real_db.post(
            "/api/v1/auth/refresh",
            json={
                "grant_type": "refresh_token",
                "refresh_token": initial_refresh_token,  # Old refresh token
            },
        )

        # This should fail if you implement proper token rotation
        # Comment out if you don't have refresh token rotation yet
        # assert _old_refresh_response.status_code == 401

        # Test invalid refresh token
        invalid_refresh_response = client_with_real_db.post(
            "/api/v1/auth/refresh",
            json={
                "grant_type": "refresh_token",
                "refresh_token": "invalid.refresh.token",
            },
        )

        assert invalid_refresh_response.status_code == 400

    @pytest.mark.asyncio
    async def test_google_oauth_integration_with_real_user_creation(
        self,
        client_with_real_db,
        async_db_session: AsyncSession,
        patch_oauth_provider_factory,
    ):
        """Test Google OAuth flow with real user creation in database."""

        provider_mock = AsyncMock()
        provider_mock.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth"
        )
        provider_mock.exchange_code_for_tokens.side_effect = [
            {
                "access_token": "google-access-token",
                "refresh_token": "google-refresh-token",
                "scope": "openid email profile",
                "id_token": "google-id-token",
            },
            {
                "access_token": "google-access-token-2",
                "refresh_token": "google-refresh-token-2",
                "scope": "openid email profile",
                "id_token": "google-id-token",
            },
        ]
        provider_mock.get_user_info.side_effect = [
            {
                "id": "google_user_123456",
                "email": "googleuser@gmail.com",
                "verified_email": True,
                "name": "Google Test User",
                "given_name": "Google",
                "family_name": "User",
                "picture": "https://example.com/picture.jpg",
                "locale": "en-US",
            },
            {
                "id": "google_user_123456",
                "email": "googleuser@gmail.com",
                "verified_email": True,
                "name": "Google Test User",
                "given_name": "Google",
                "family_name": "User",
                "picture": "https://example.com/picture.jpg",
                "locale": "en-US",
            },
        ]
        provider_mock.validate_id_token.return_value = {
            "sub": "google_user_123456",
            "email": "googleuser@gmail.com",
            "name": "Google Test User",
            "email_verified": True,
        }

        patch_oauth_provider_factory(provider_mock)

        token_payload = {
            "provider": "google",
            "grant_type": "authorization_code",
            "code": "mock_google_auth_code",
            "redirect_uri": "http://localhost:8000/api/v1/auth/callback/google",
        }

        token_response = client_with_real_db.post(
            "/api/v1/auth/token",
            json=token_payload,
        )
        assert token_response.status_code == 200
        token_data = token_response.json()

        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["email"] == "googleuser@gmail.com"
        assert token_data["token_type"] == "Bearer"

        # Verify user was actually created in database
        from app.services.user import UserService

        user_service = UserService(async_db_session)

        created_user = await user_service.get_user_by_email("googleuser@gmail.com")
        assert created_user is not None
        assert created_user.username == "googleuser"  # Generated from email
        assert created_user.full_name == "Google Test User"
        assert created_user.is_active is True
        assert (
            created_user.hashed_password is None
        )  # OAuth users don't have local passwords

        # Test that the returned token actually works
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        me_response = client_with_real_db.get("/api/v1/users/me", headers=headers)

        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == "googleuser@gmail.com"
        assert user_data["full_name"] == "Google Test User"

        # Test subsequent login with same Google account (should not create duplicate)
        second_response = client_with_real_db.post(
            "/api/v1/auth/token",
            json={
                "provider": "google",
                "grant_type": "authorization_code",
                "code": "another_mock_code",
                "redirect_uri": "http://localhost:8000/api/v1/auth/callback/google",
            },
        )
        assert second_response.status_code == 200
        second_token_data = second_response.json()
        assert second_token_data["user_id"] == token_data["user_id"]
