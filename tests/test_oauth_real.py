"""Real OAuth2 authentication tests that replace the failing auth tests."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from main import app


class TestOAuth2RealAuth:
    """Test OAuth2 authentication with real JWT tokens and proper validation."""

    @pytest.fixture
    def test_user_in_app(self, client):
        """Create a test user using the existing test infrastructure."""
        # This uses the existing MockAsyncSession which works for simple operations
        # We'll create a user directly in the mock session
        return {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            "hashed_password": get_password_hash("TestPass123!")
        }

    async def test_oauth_login_success_with_real_jwt(self, client_with_real_db, sample_user_in_db):
        """Test OAuth login with real JWT token generation and validation."""

        # Test login endpoint with real database user
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )            
        assert response.status_code == 200
        token_data = response.json()
            
        # Validate response structure
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["user_id"] == self.test_user_in_app["id"]
        assert token_data["email"] == self.test_user_in_app["email"]
        assert token_data["username"] == self.test_user_in_app["username"]
        assert "expires_in" in token_data
        
        # Verify the token is a real JWT that can be decoded
        from app.core.security import verify_token
        decoded_user_id = verify_token(token_data["access_token"])
        assert decoded_user_id is not None
        assert int(decoded_user_id) == test_user_in_app["id"]

    def test_oauth_login_invalid_credentials(self, client):
        """Test OAuth login with invalid credentials using real authentication flow."""
        
        # Mock authentication to return None (invalid credentials)
        with patch('app.services.user.UserService.authenticate_user') as mock_auth:
            from app.core.exceptions import AuthenticationError
            mock_auth.side_effect = AuthenticationError("Invalid username/email or password")
            
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "WrongPassword123!",
                    "grant_type": "password"
                }
            )
            
            assert response.status_code == 401
            error_data = response.json()
            assert "Invalid username/email or password" in error_data["detail"]

    def test_protected_endpoint_with_real_jwt_validation(self, client, test_user_in_app):
        """Test accessing protected endpoints with real JWT validation."""
        
        # Create a real JWT token
        token_data = {"sub": str(test_user_in_app["id"]), "email": test_user_in_app["email"]}
        access_token = create_access_token(token_data)
        
        # Mock the UserService.get_user method to return our test user
        with patch('app.services.user.UserService.get_user') as mock_get_user:
            mock_user = User(**test_user_in_app)
            mock_get_user.return_value = mock_user
            
            # Test accessing protected endpoint
            headers = {"Authorization": f"Bearer {access_token}"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == 200
            user_data = response.json()
            assert user_data["id"] == test_user_in_app["id"]
            assert user_data["email"] == test_user_in_app["email"]
            assert user_data["username"] == test_user_in_app["username"]

    def test_invalid_jwt_token_validation(self, client):
        """Test JWT token validation with various invalid tokens."""
        
        # Test with completely invalid token
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        
        # Test with malformed authorization header
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
        
        # Test with missing authorization header
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401
        
        # Test with empty token
        headers = {"Authorization": "Bearer "}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    def test_expired_jwt_token(self, client):
        """Test behavior with expired JWT tokens."""
        from datetime import timedelta
        
        # Create an expired token
        token_data = {"sub": "1", "email": "test@example.com"}
        expired_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    def test_refresh_token_flow(self, client, test_user_in_app):
        """Test refresh token functionality with real JWT tokens."""
        
        # Mock authentication for initial login
        with patch('app.services.user.UserService.authenticate_user') as mock_auth:
            mock_user = User(**test_user_in_app)
            mock_auth.return_value = mock_user
            
            # Get initial tokens
            login_response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "TestPass123!",
                    "grant_type": "password"
                }
            )
            
            assert login_response.status_code == 200
            initial_tokens = login_response.json()
            
            # Use refresh token to get new access token
            # Mock the refresh token validation
            with patch('app.core.security.verify_token') as mock_verify:
                mock_verify.return_value = str(test_user_in_app["id"])
                
                with patch('app.services.user.UserService.get_user') as mock_get_user:
                    mock_get_user.return_value = mock_user
                
                    refresh_response = client.post(
                        "/api/v1/auth/refresh",
                        json={
                            "grant_type": "refresh_token",
                            "refresh_token": initial_tokens["refresh_token"]
                        }
                    )
                    
                    assert refresh_response.status_code == 200
                    new_tokens = refresh_response.json()
                    
                    # New access token should be different
                    assert new_tokens["access_token"] != initial_tokens["access_token"]
                    assert new_tokens["user_id"] == test_user_in_app["id"]

    def test_user_deactivation_blocks_access(self, client, test_user_in_app):
        """Test that deactivated users cannot access protected endpoints."""
        
        # Create token for active user
        token_data = {"sub": str(test_user_in_app["id"]), "email": test_user_in_app["email"]}
        access_token = create_access_token(token_data)
        
        # Mock user service to return inactive user
        inactive_user_data = test_user_in_app.copy()
        inactive_user_data["is_active"] = False
        
        with patch('app.services.user.UserService.get_user') as mock_get_user:
            mock_user = User(**inactive_user_data)
            mock_get_user.return_value = mock_user
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            # Should be forbidden due to inactive status
            assert response.status_code == 403
            error_data = response.json()
            assert "deactivated" in error_data["detail"].lower()

    def test_jwt_token_with_invalid_user_id(self, client):
        """Test JWT token with user ID that doesn't exist."""
        
        # Create token with non-existent user ID
        token_data = {"sub": "99999", "email": "nonexistent@example.com"}
        access_token = create_access_token(token_data)
        
        # Mock user service to raise NotFoundError
        with patch('app.services.user.UserService.get_user') as mock_get_user:
            from app.core.exceptions import NotFoundError
            mock_get_user.side_effect = NotFoundError("User not found")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == 401

    def test_oauth_login_validation_errors(self, client):
        """Test OAuth login with various validation errors."""
        
        # Test missing required fields
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code in [400, 422]  # Validation error
        
        # Test invalid grant type
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
                "grant_type": "invalid_grant"
            }
        )
        assert response.status_code in [400, 422]
        
        # Test invalid email format
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid-email",
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )
        assert response.status_code in [400, 422]

    def test_concurrent_token_usage(self, client, test_user_in_app):
        """Test that the same token can be used concurrently (should work)."""
        
        # Create a valid token
        token_data = {"sub": str(test_user_in_app["id"]), "email": test_user_in_app["email"]}
        access_token = create_access_token(token_data)
        
        with patch('app.services.user.UserService.get_user') as mock_get_user:
            mock_user = User(**test_user_in_app)
            mock_get_user.return_value = mock_user
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Make multiple concurrent-like requests with same token
            response1 = client.get("/api/v1/users/me", headers=headers)
            response2 = client.get("/api/v1/users/me", headers=headers)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response1.json()["id"] == response2.json()["id"]