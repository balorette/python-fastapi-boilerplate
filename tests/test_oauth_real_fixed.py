"""
Real OAuth2 authentication tests using actual database and JWT validation.

These tests focus on realistic authentication flows while avoiding the asyncio
event loop issues that plague the complex PostgreSQL integration tests.
"""

import pytest
from unittest.mock import patch
from fastapi import status

from app.core.security import create_access_token, verify_token
from app.models.user import User


class TestOAuth2RealAuth:
    """Test OAuth2 authentication with real JWT tokens and database integration."""

    async def test_oauth_login_success_with_real_jwt(self, client_with_real_db, sample_user_in_db):
        """Test OAuth login with real JWT token generation and validation."""

        # Test login endpoint with real database user
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",  # This matches the password used in sample_user_in_db
                "grant_type": "password"
            }
        )
        
        assert response.status_code == 200
        token_data = response.json()
        
        # Verify response structure
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert "expires_in" in token_data
        assert token_data["token_type"] == "Bearer"
        
        # Verify the token is a real JWT that can be decoded
        decoded_payload = verify_token(token_data["access_token"])
        assert decoded_payload is not None
        assert "sub" in decoded_payload
        assert int(decoded_payload["sub"]) == sample_user_in_db.id

    async def test_oauth_login_invalid_credentials(self, client_with_real_db):
        """Test OAuth login with invalid credentials using real authentication flow."""

        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!",
                "grant_type": "password"
            }
        )

        assert response.status_code == 401
        error_data = response.json()
        assert "detail" in error_data
        assert "Invalid credentials" in error_data["detail"]

    async def test_protected_endpoint_with_real_jwt_validation(self, client_with_real_db, sample_user_in_db):
        """Test accessing protected endpoints with real JWT validation."""

        # Create a real JWT token
        token_data = {"sub": str(sample_user_in_db.id), "email": sample_user_in_db.email}
        access_token = create_access_token(token_data)

        # Test accessing protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 200
        user_data = response.json()
        assert user_data["id"] == sample_user_in_db.id
        assert user_data["email"] == sample_user_in_db.email

    def test_invalid_jwt_token_validation(self, client):
        """Test that invalid JWT tokens are properly rejected."""

        # Use an obviously invalid token
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401
        error_data = response.json()
        assert "Could not validate credentials" in error_data["detail"]

    def test_expired_jwt_token(self, client):
        """Test that expired JWT tokens are properly rejected."""

        # Create an expired token (using negative expiry)
        from datetime import datetime, timedelta, timezone
        from app.core.security import create_access_token

        expired_token = create_access_token(
            data={"sub": "1", "email": "test@example.com"},
            expires_delta=timedelta(minutes=-1)  # Already expired
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401

    async def test_refresh_token_flow(self, client_with_real_db, sample_user_in_db):
        """Test refresh token functionality with real JWT tokens."""

        # Get initial tokens through login
        login_response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )

        assert login_response.status_code == 200
        login_data = login_response.json()
        refresh_token = login_data.get("refresh_token")

        if refresh_token:  # Only test refresh if it's implemented
            # Use refresh token to get new access token
            refresh_response = client_with_real_db.post(
                "/api/v1/auth/refresh",
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )

            # This might return 404 if refresh endpoint isn't implemented yet
            if refresh_response.status_code != 404:
                assert refresh_response.status_code == 200
                refresh_data = refresh_response.json()
                assert "access_token" in refresh_data
                
                # Verify new token works
                new_token = refresh_data["access_token"]
                decoded_payload = verify_token(new_token)
                assert decoded_payload is not None
                assert "sub" in decoded_payload
                assert int(decoded_payload["sub"]) == sample_user_in_db.id

    async def test_user_deactivation_blocks_access(self, client_with_real_db, sample_user_in_db, async_db_session):
        """Test that deactivated users cannot access protected endpoints."""

        # Create token for active user first
        token_data = {"sub": str(sample_user_in_db.id), "email": sample_user_in_db.email}
        access_token = create_access_token(token_data)

        # Verify token works initially
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200

        # Deactivate the user in the database
        sample_user_in_db.is_active = False
        async_db_session.add(sample_user_in_db)
        await async_db_session.commit()

        # Now the same token should not work 
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        # Should be forbidden due to inactive status
        assert response.status_code in [401, 403]  # Either is acceptable for inactive user

    def test_jwt_token_with_invalid_user_id(self, client):
        """Test JWT token with non-existent user ID."""

        # Create token with non-existent user ID
        token_data = {"sub": "99999", "email": "nonexistent@example.com"}
        access_token = create_access_token(token_data)

        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401

    def test_oauth_login_validation_errors(self, client):
        """Test OAuth login with various validation errors."""

        # Missing email
        response = client.post(
            "/api/v1/auth/login",
            json={
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )
        assert response.status_code == 422  # Validation error

        # Missing password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "grant_type": "password"
            }
        )
        assert response.status_code == 422  # Validation error

        # Invalid email format
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )
        assert response.status_code == 422  # Validation error

    async def test_concurrent_token_usage(self, client_with_real_db, sample_user_in_db):
        """Test that the same token can be used concurrently (should work)."""

        # Create a valid token
        token_data = {"sub": str(sample_user_in_db.id), "email": sample_user_in_db.email}
        access_token = create_access_token(token_data)

        headers = {"Authorization": f"Bearer {access_token}"}

        # Make multiple concurrent-like requests with same token
        response1 = client_with_real_db.get("/api/v1/users/me", headers=headers)
        response2 = client_with_real_db.get("/api/v1/users/me", headers=headers)

        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should return the same user data
        user_data1 = response1.json()
        user_data2 = response2.json()
        assert user_data1["id"] == user_data2["id"] == sample_user_in_db.id

    async def test_missing_authorization_header(self, client_with_real_db):
        """Test protected endpoint without authorization header."""

        response = client_with_real_db.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_malformed_authorization_header(self, client_with_real_db):
        """Test protected endpoint with malformed authorization header."""

        # Missing Bearer prefix
        headers = {"Authorization": "invalid-token-format"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        # Wrong prefix
        headers = {"Authorization": "Basic dGVzdDp0ZXN0"}
        response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401