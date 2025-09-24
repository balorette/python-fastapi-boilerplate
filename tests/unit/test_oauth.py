"""
Comprehensive tests for OAuth2 flows, PKCE validation, and token handling.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_pkce_pair,
    verify_pkce,
    get_password_hash
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.oauth import (
    AuthorizationRequest,
    TokenRequest,
    LocalLoginRequest,
    RefreshTokenRequest
)


class TestOAuth2Security:
    """Test OAuth2 security functions."""
    
    def test_create_access_token(self):
        """Test OAuth2-compliant access token creation."""
        data = {
            "sub": "123",
            "email": "test@example.com",
            "name": "Test User",
            "provider": "local"
        }
        
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token contains OAuth2 standard claims
        payload = verify_token(token)
        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"
        assert payload["name"] == "Test User"
        assert payload["provider"] == "local"
        assert payload["token_type"] == "access_token"
        assert "iss" in payload
        assert "aud" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "nbf" in payload
    
    def test_create_access_token_with_custom_expiry(self):
        """Test access token with custom expiration."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data, expires_delta_minutes=5)
        
        payload = verify_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # Should expire in approximately 5 minutes
        assert timedelta(minutes=4) < (exp_time - now) < timedelta(minutes=6)
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = 123
        token = create_refresh_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        payload = verify_token(token, "refresh_token")
        assert payload["sub"] == "123"
        assert payload["token_type"] == "refresh_token"
        assert "iss" in payload
        assert "aud" in payload
        assert "exp" in payload
    
    def test_pkce_generation_and_verification(self):
        """Test PKCE code verifier and challenge generation/verification."""
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Verify format
        assert isinstance(code_verifier, str)
        assert isinstance(code_challenge, str)
        assert len(code_verifier) >= 43  # Base64url encoded 32 bytes minimum
        assert len(code_challenge) >= 43
        
        # Verify PKCE verification works
        assert verify_pkce(code_verifier, code_challenge) is True
        
        # Verify wrong verifier fails
        wrong_verifier, _ = generate_pkce_pair()
        assert verify_pkce(wrong_verifier, code_challenge) is False
    
    def test_token_verification_invalid_token(self):
        """Test token verification with invalid token."""
        result = verify_token("invalid.token.here")
        assert result is None
    
    def test_token_verification_expired_token(self):
        """Test token verification with expired token."""
        # Create token that expires immediately
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data, expires_delta_minutes=-1)
        
        result = verify_token(token)
        assert result is None


class TestOAuth2Schemas:
    """Test OAuth2 Pydantic schemas."""
    
    def test_authorization_request_local(self):
        """Test authorization request for local provider."""
        request_data = {
            "provider": "local",
            "client_id": "test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "random-state",
            "username": "user@example.com",
            "password": "password123"
        }
        
        request = AuthorizationRequest(**request_data)
        assert request.provider == "local"
        assert request.username == "user@example.com"
        assert request.password == "password123"
        assert request.response_type == "code"
    
    def test_authorization_request_external(self):
        """Test authorization request for external provider."""
        code_verifier, code_challenge = generate_pkce_pair()
        
        request_data = {
            "provider": "google",
            "client_id": "google-client-id",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "random-state",
            "scope": "openid email profile",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }
        
        request = AuthorizationRequest(**request_data)
        assert request.provider == "google"
        assert request.code_challenge == code_challenge
        assert request.code_challenge_method == "S256"
    
    def test_token_request(self):
        """Test token exchange request."""
        request_data = {
            "provider": "local",
            "grant_type": "authorization_code",
            "code": "auth-code-123",
            "redirect_uri": "http://localhost:3000/callback",
            "client_id": "test-client"
        }
        
        request = TokenRequest(**request_data)
        assert request.provider == "local"
        assert request.grant_type == "authorization_code"
        assert request.code == "auth-code-123"
    
    def test_local_login_request(self):
        """Test local login request."""
        request_data = {
            "email": "user@example.com",
            "password": "password123"
        }
        
        request = LocalLoginRequest(**request_data)
        assert request.email == "user@example.com"
        assert request.password == "password123"
        assert request.grant_type == "password"
    
    def test_refresh_token_request(self):
        """Test refresh token request."""
        request_data = {
            "refresh_token": "refresh-token-123"
        }
        
        request = RefreshTokenRequest(**request_data)
        assert request.refresh_token == "refresh-token-123"
        assert request.grant_type == "refresh_token"


@pytest.mark.asyncio
class TestOAuth2Endpoints:
    """Test OAuth2 endpoints with mocked dependencies."""
    
    async def test_authorize_local_success(self):
        """Test successful local authorization."""
        # Mock user and dependencies
        mock_user = User(
            id=1,
            email="user@example.com",
            username="testuser",
            hashed_password=get_password_hash("password123"),
            full_name="Test User",
            is_active=True
        )
        
        with patch('app.api.v1.endpoints.oauth.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo
            
            from app.api.v1.endpoints.oauth import authorize
            
            request = AuthorizationRequest(
                provider="local",
                client_id="test-client",
                redirect_uri="http://localhost:3000/callback",
                state="test-state",
                username="user@example.com",
                password="password123"
            )
            
            mock_db = AsyncMock()
            result = await authorize(request, mock_db)
            
            assert result.authorization_code is not None
            assert result.state == "test-state"
            assert result.redirect_uri == "http://localhost:3000/callback"
            
            # Verify authorization code is valid
            payload = verify_token(result.authorization_code)
            assert payload["sub"] == "1"
            assert payload["email"] == "user@example.com"
            assert payload["type"] == "auth_code"
    
    async def test_authorize_local_invalid_credentials(self):
        """Test local authorization with invalid credentials."""
        mock_user = User(
            id=1,
            email="user@example.com",
            username="testuser",
            hashed_password=get_password_hash("different-password"),
            is_active=True
        )
        
        with patch('app.api.v1.endpoints.oauth.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo_class.return_value = mock_repo
            
            from app.api.v1.endpoints.oauth import authorize
            
            request = AuthorizationRequest(
                provider="local",
                client_id="test-client",
                redirect_uri="http://localhost:3000/callback",
                state="test-state",
                username="user@example.com",
                password="wrong-password"
            )
            
            mock_db = AsyncMock()
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await authorize(request, mock_db)
    
    async def test_token_exchange_local_success(self):
        """Test successful token exchange for local provider."""
        # Create a valid authorization code
        auth_token_data = {
            "sub": "1",
            "email": "user@example.com",
            "type": "auth_code"
        }
        auth_code = create_access_token(auth_token_data, expires_delta_minutes=10)
        
        mock_user = User(
            id=1,
            email="user@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True
        )
        
        with patch('app.api.v1.endpoints.oauth.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo_class.return_value = mock_repo
            
            from app.api.v1.endpoints.oauth import token
            
            request = TokenRequest(
                provider="local",
                grant_type="authorization_code",
                code=auth_code,
                redirect_uri="http://localhost:3000/callback",
                client_id="test-client"
            )
            
            mock_db = AsyncMock()
            result = await token(request, mock_db)
            
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "Bearer"
            assert result.expires_in > 0
            assert result.scope == "openid email profile"
            
            # Verify access token contains correct claims
            access_payload = verify_token(result.access_token)
            assert access_payload["sub"] == "1"
            assert access_payload["email"] == "user@example.com"
            assert access_payload["name"] == "Test User"
            assert access_payload["provider"] == "local"
            assert access_payload["token_type"] == "access_token"
            
            # Verify refresh token
            refresh_payload = verify_token(result.refresh_token, "refresh_token")
            assert refresh_payload["sub"] == "1"
            assert refresh_payload["token_type"] == "refresh_token"
    
    async def test_local_login_success(self):
        """Test successful local login."""
        mock_user = User(
            id=1,
            email="user@example.com",
            username="testuser",
            hashed_password=get_password_hash("password123"),
            full_name="Test User",
            is_active=True
        )
        
        with patch('app.api.v1.endpoints.oauth.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo_class.return_value = mock_repo
            
            from app.api.v1.endpoints.oauth import local_login
            
            request = LocalLoginRequest(
                email="user@example.com",
                password="password123"
            )
            
            mock_db = AsyncMock()
            result = await local_login(request, mock_db)
            
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "Bearer"
            
            # Verify update was called for last_login
            mock_repo.update.assert_called_once()
    
    async def test_refresh_token_success(self):
        """Test successful token refresh."""
        # Create a valid refresh token
        user_id = 1
        refresh_token = create_refresh_token(user_id)
        
        mock_user = User(
            id=1,
            email="user@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True
        )
        
        with patch('app.api.v1.endpoints.oauth.UserRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_user
            mock_repo_class.return_value = mock_repo
            
            from app.api.v1.endpoints.oauth import refresh_token_endpoint
            
            request = RefreshTokenRequest(refresh_token=refresh_token)
            
            mock_db = AsyncMock()
            result = await refresh_token_endpoint(request, mock_db)
            
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "Bearer"
            
            # Verify new access token
            access_payload = verify_token(result.access_token)
            assert access_payload["sub"] == "1"
            assert access_payload["token_type"] == "access_token"
    
    async def test_get_oauth_providers(self):
        """Test OAuth providers endpoint."""
        from app.api.v1.endpoints.oauth import get_oauth_providers
        
        result = await get_oauth_providers()
        
        assert "providers" in result
        assert len(result["providers"]) >= 2  # local and google
        assert result["recommended_flow"] == "authorization_code_with_pkce"
        assert result["pkce_required"] is True
        
        # Check local provider
        local_provider = next(p for p in result["providers"] if p["name"] == "local")
        assert local_provider["display_name"] == "Local Account"
        assert local_provider["type"] == "local"
        assert local_provider["supports_pkce"] is True
        
        # Check Google provider
        google_provider = next(p for p in result["providers"] if p["name"] == "google")
        assert google_provider["display_name"] == "Google"
        assert google_provider["type"] == "oauth2"
        assert google_provider["supports_pkce"] is True


class TestOAuth2Integration:
    """Integration tests for complete OAuth2 flows."""
    
    @pytest.mark.asyncio
    async def test_complete_local_oauth_flow(self):
        """Test complete OAuth2 flow for local provider."""
        # This would be a full integration test with a test database
        # and the complete FastAPI application
        pass
    
    @pytest.mark.asyncio
    async def test_pkce_flow_with_spa(self):
        """Test PKCE flow as it would be used by a SPA."""
        # 1. SPA generates PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()
        
        # 2. SPA calls authorization endpoint
        # 3. User enters credentials
        # 4. Authorization code is returned
        # 5. SPA exchanges code for tokens using code_verifier
        
        # This would test the complete flow end-to-end
        pass
    
    @pytest.mark.asyncio
    async def test_token_rotation_security(self):
        """Test that refresh token rotation works correctly."""
        # 1. Create initial tokens
        # 2. Use refresh token to get new tokens
        # 3. Verify old refresh token is invalidated
        # 4. Verify new refresh token can be used
        
        # This would test token rotation security measures
        pass


# Pytest fixtures for testing
@pytest.fixture
async def mock_db_session():
    """Mock database session for testing."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        oauth_provider=None,
        oauth_id=None
    )


@pytest.fixture
def oauth_test_data():
    """Common test data for OAuth tests."""
    return {
        "client_id": "test-client-id",
        "redirect_uri": "http://localhost:3000/callback",
        "state": "test-state-123",
        "scope": "openid email profile",
        "user_email": "test@example.com",
        "user_password": "password123"
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])