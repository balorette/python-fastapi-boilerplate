"""
Simplified OAuth2 JWT validation tests.

These tests focus on realistic JWT token validation and authentication flows
while avoiding the complex asyncio event loop issues that plague async database tests.
Uses MockAsyncSession for database operations but real JWT token generation and validation.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token, verify_token, get_password_hash
from app.models.user import User


class TestOAuth2JWTValidation:
    """Test OAuth2 authentication focusing on JWT token validation."""

    @pytest.fixture
    def test_user_in_app(self, client):
        """Create a test user using the existing test infrastructure."""
        return {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            "hashed_password": get_password_hash("TestPass123!")
        }

    def test_oauth_login_success_with_real_jwt(self, client, test_user_in_app):
        """Test OAuth login with real JWT token generation and validation."""

        # Mock the UserRepository methods
        with patch('app.repositories.user.UserRepository.get_by_email') as mock_get_by_email, \
             patch('app.repositories.user.UserRepository.update') as mock_update:
            
            # Create User object from test data
            user_obj = User(
                id=test_user_in_app["id"],
                email=test_user_in_app["email"],
                username=test_user_in_app.get("username", "testuser"),
                full_name=test_user_in_app["full_name"],
                hashed_password=test_user_in_app["hashed_password"],
                is_active=test_user_in_app["is_active"]
            )
            
            mock_get_by_email.return_value = user_obj
            mock_update.return_value = user_obj  # Return updated user

            # Test login endpoint
            response = client.post(
                "/api/v1/oauth/login",
                json={
                    "email": "test@example.com",
                    "password": "TestPass123!",
                    "grant_type": "password"
                }
            )

            assert response.status_code == 200
            token_data = response.json()

            # Verify response structure (OAuth2 compliant)
            assert "access_token" in token_data
            assert "token_type" in token_data
            assert "expires_in" in token_data
            assert token_data["token_type"] == "Bearer"

            # Verify the token is a real JWT that can be decoded
            decoded_payload = verify_token(token_data["access_token"])
            assert decoded_payload is not None
            assert "sub" in decoded_payload
            assert int(decoded_payload["sub"]) == test_user_in_app["id"]
            assert decoded_payload["email"] == test_user_in_app["email"]

            # Verify JWT standard claims are present
            assert "exp" in decoded_payload  # Expiration
            assert "iat" in decoded_payload  # Issued at
            assert "iss" in decoded_payload  # Issuer
            assert "aud" in decoded_payload  # Audience

    def test_oauth_login_invalid_credentials(self, client):
        """Test OAuth login with invalid credentials."""

        with patch('app.repositories.user.UserRepository.get_by_email') as mock_get_by_email:
            # Return None to simulate user not found
            mock_get_by_email.return_value = None

            response = client.post(
                "/api/v1/oauth/login",
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

    def test_oauth_login_wrong_password(self, client, test_user_in_app):
        """Test OAuth login with correct email but wrong password."""

        with patch('app.repositories.user.UserRepository.get_by_email') as mock_get_by_email:
            # Return user but password won't match
            user_obj = User(
                id=test_user_in_app["id"],
                email=test_user_in_app["email"],
                username=test_user_in_app.get("username", "testuser"),
                full_name=test_user_in_app["full_name"],
                hashed_password=get_password_hash("DifferentPassword123!"),  # Different password
                is_active=test_user_in_app["is_active"]
            )
            
            mock_get_by_email.return_value = user_obj

            response = client.post(
                "/api/v1/oauth/login",
                json={
                    "email": "test@example.com",
                    "password": "TestPass123!",  # Correct password but hash won't match
                    "grant_type": "password"
                }
            )

            assert response.status_code == 401

    def test_oauth_login_inactive_user(self, client, test_user_in_app):
        """Test OAuth login with inactive user account."""

        with patch('app.repositories.user.UserRepository.get_by_email') as mock_get_by_email:
            # Create inactive user
            inactive_user = User(
                id=test_user_in_app["id"],
                email=test_user_in_app["email"],
                username=test_user_in_app.get("username", "testuser"),
                full_name=test_user_in_app["full_name"],
                hashed_password=test_user_in_app["hashed_password"],
                is_active=False  # Inactive user
            )
            
            mock_get_by_email.return_value = inactive_user

            response = client.post(
                "/api/v1/oauth/login",
                json={
                    "email": "test@example.com",
                    "password": "TestPass123!",
                    "grant_type": "password"
                }
            )

            assert response.status_code == 403
            error_data = response.json()
            assert "Account is disabled" in error_data["detail"]

    def test_protected_endpoint_with_valid_jwt(self, client, test_user_in_app):
        """Test accessing protected endpoints with valid JWT token."""

        # Create a real JWT token
        token_data = {
            "sub": str(test_user_in_app["id"]), 
            "email": test_user_in_app["email"]
        }
        access_token = create_access_token(token_data)

        # Mock the UserService.get_user method
        with patch('app.services.user.UserService.get_user') as mock_get_user:
            user_obj = User(
                id=test_user_in_app["id"],
                email=test_user_in_app["email"],
                username=test_user_in_app.get("username", "testuser"),
                full_name=test_user_in_app["full_name"],
                is_active=test_user_in_app["is_active"]
            )
            mock_get_user.return_value = user_obj

            # Test accessing protected endpoint
            headers = {"Authorization": f"Bearer {access_token}"}
            response = client.get("/api/v1/users/me", headers=headers)

            assert response.status_code == 200
            user_data = response.json()
            assert user_data["id"] == test_user_in_app["id"]
            assert user_data["email"] == test_user_in_app["email"]

    def test_protected_endpoint_invalid_token(self, client):
        """Test protected endpoint with invalid JWT token."""

        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401
        error_data = response.json()
        assert "Could not validate credentials" in error_data["detail"]

    def test_protected_endpoint_expired_token(self, client):
        """Test protected endpoint with expired JWT token."""

        # Create an expired token
        expired_token = create_access_token(
            data={"sub": "1", "email": "test@example.com"},
            expires_delta=timedelta(minutes=-1)  # Already expired
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401

    def test_protected_endpoint_no_authorization(self, client):
        """Test protected endpoint without authorization header."""

        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_protected_endpoint_malformed_header(self, client):
        """Test protected endpoint with malformed authorization header."""

        # Missing Bearer prefix
        headers = {"Authorization": "invalid-token-format"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

        # Wrong prefix
        headers = {"Authorization": "Basic dGVzdDp0ZXN0"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    def test_jwt_token_with_nonexistent_user(self, client):
        """Test JWT token with non-existent user ID."""

        # Create token with non-existent user ID
        token_data = {"sub": "99999", "email": "nonexistent@example.com"}
        access_token = create_access_token(token_data)

        with patch('app.services.user.UserService.get_user') as mock_get_user:
            # Return None to simulate user not found
            mock_get_user.return_value = None

            headers = {"Authorization": f"Bearer {access_token}"}
            response = client.get("/api/v1/users/me", headers=headers)

            assert response.status_code == 401

    def test_jwt_token_payload_structure(self, test_user_in_app):
        """Test that JWT tokens contain proper OAuth2/OIDC standard claims."""

        token_data = {
            "sub": str(test_user_in_app["id"]),
            "email": test_user_in_app["email"],
            "name": test_user_in_app["full_name"]
        }
        
        access_token = create_access_token(token_data)
        decoded_payload = verify_token(access_token)
        
        assert decoded_payload is not None
        
        # Verify OAuth2/OIDC standard claims
        assert "sub" in decoded_payload  # Subject (user ID)
        assert "exp" in decoded_payload  # Expiration time
        assert "iat" in decoded_payload  # Issued at
        assert "nbf" in decoded_payload  # Not before
        assert "iss" in decoded_payload  # Issuer
        assert "aud" in decoded_payload  # Audience
        assert "token_type" in decoded_payload  # Token type
        
        # Verify custom claims
        assert decoded_payload["email"] == test_user_in_app["email"]
        assert decoded_payload["name"] == test_user_in_app["full_name"]
        assert decoded_payload["token_type"] == "access_token"

    def test_token_expiration_time(self):
        """Test that tokens have correct expiration time."""

        # Create token with specific expiration
        custom_expiry = timedelta(minutes=30)
        token_data = {"sub": "1", "email": "test@example.com"}
        access_token = create_access_token(token_data, expires_delta=custom_expiry)
        
        decoded_payload = verify_token(access_token)
        assert decoded_payload is not None
        
        # Check expiration is approximately correct (within 1 minute tolerance)
        exp_timestamp = decoded_payload["exp"]
        expected_exp = datetime.now(timezone.utc) + custom_expiry
        actual_exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        
        time_diff = abs((actual_exp - expected_exp).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_oauth_validation_errors(self, client):
        """Test OAuth login with various validation errors."""

        # Missing email
        response = client.post(
            "/api/v1/oauth/login",
            json={
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )
        assert response.status_code == 422  # Validation error

        # Missing password  
        response = client.post(
            "/api/v1/oauth/login",
            json={
                "email": "test@example.com",
                "grant_type": "password"
            }
        )
        assert response.status_code == 422  # Validation error

        # Invalid email format
        response = client.post(
            "/api/v1/oauth/login",
            json={
                "email": "not-an-email",
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )
        assert response.status_code == 422  # Validation error

        # Invalid grant type
        response = client.post(
            "/api/v1/oauth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
                "grant_type": "client_credentials"  # Wrong grant type
            }
        )
        assert response.status_code == 422  # Validation error

    def test_concurrent_token_usage(self, client, test_user_in_app):
        """Test that the same token can be used concurrently."""

        # Create a valid token
        token_data = {"sub": str(test_user_in_app["id"]), "email": test_user_in_app["email"]}
        access_token = create_access_token(token_data)

        with patch('app.services.user.UserService.get_user') as mock_get_user:
            user_obj = User(
                id=test_user_in_app["id"],
                email=test_user_in_app["email"],
                username=test_user_in_app.get("username", "testuser"),
                full_name=test_user_in_app["full_name"],
                is_active=test_user_in_app["is_active"]
            )
            mock_get_user.return_value = user_obj

            headers = {"Authorization": f"Bearer {access_token}"}

            # Make multiple requests with same token
            response1 = client.get("/api/v1/users/me", headers=headers)
            response2 = client.get("/api/v1/users/me", headers=headers)

            assert response1.status_code == 200
            assert response2.status_code == 200
            
            # Both should return the same user data
            user_data1 = response1.json()
            user_data2 = response2.json()
            assert user_data1["id"] == user_data2["id"] == test_user_in_app["id"]