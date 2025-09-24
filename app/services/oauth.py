"""OAuth service for Google authentication."""

import secrets
from typing import Optional, Dict, Any
import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from urllib.parse import urlencode

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError
from app.schemas.oauth import GoogleUserInfo, GoogleTokenResponse


class GoogleOAuthService:
    """Service for handling Google OAuth authentication."""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # Google OAuth endpoints
        self.auth_uri = "https://accounts.google.com/o/oauth2/auth"
        self.token_uri = "https://oauth2.googleapis.com/token"
        self.userinfo_uri = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # OAuth scopes
        self.scopes = [
            "openid",
            "profile", 
            "email"
        ]
    
    def generate_auth_url(self, state: Optional[str] = None) -> tuple[str, str]:
        """Generate Google OAuth authorization URL with CSRF protection.
        
        Returns:
            tuple: (auth_url, state) where state is for CSRF protection
        """
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "state": state,
        }
        
        auth_url = f"{self.auth_uri}?{urlencode(params)}"
        return auth_url, state
    
    async def exchange_code_for_tokens(self, code: str) -> GoogleTokenResponse:
        """Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from Google
            
        Returns:
            GoogleTokenResponse containing tokens
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_uri, data=data)
                response.raise_for_status()
                token_data = response.json()
            
            # Validate required fields
            if "access_token" not in token_data:
                raise AuthenticationError("No access token received from Google")
            
            return GoogleTokenResponse(**token_data)
            
        except httpx.HTTPError as e:
            raise AuthenticationError(f"Failed to exchange code for tokens: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token exchange error: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user information from Google using access token.
        
        Args:
            access_token: Google access token
            
        Returns:
            GoogleUserInfo containing user data
            
        Raises:
            AuthenticationError: If user info retrieval fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.userinfo_uri, headers=headers)
                response.raise_for_status()
                user_data = response.json()
            
            # Validate required fields
            required_fields = ["id", "email", "name"]
            for field in required_fields:
                if field not in user_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            return GoogleUserInfo(**user_data)
            
        except httpx.HTTPError as e:
            raise AuthenticationError(f"Failed to get user info: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"User info error: {str(e)}")
    
    def verify_id_token(self, id_token_str: str) -> Dict[str, Any]:
        """Verify Google ID token and extract user information.
        
        Args:
            id_token_str: Google ID token string
            
        Returns:
            dict: Verified token payload
            
        Raises:
            AuthenticationError: If token verification fails
        """
        try:
            # Verify the token
            request = google_requests.Request()
            id_info = id_token.verify_oauth2_token(
                id_token_str, request, self.client_id
            )
            
            # Verify issuer
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise AuthenticationError("Invalid token issuer")
            
            return id_info
            
        except ValueError as e:
            raise AuthenticationError(f"Invalid ID token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token verification error: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> GoogleTokenResponse:
        """Refresh Google access token using refresh token.
        
        Args:
            refresh_token: Google refresh token
            
        Returns:
            GoogleTokenResponse with new access token
            
        Raises:
            AuthenticationError: If token refresh fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.token_uri, data=data)
                response.raise_for_status()
                token_data = response.json()
            
            # Add refresh token to response if not included
            if "refresh_token" not in token_data:
                token_data["refresh_token"] = refresh_token
            
            return GoogleTokenResponse(**token_data)
            
        except httpx.HTTPError as e:
            raise AuthenticationError(f"Failed to refresh token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token refresh error: {str(e)}")
    
    def is_enabled(self) -> bool:
        """Check if Google OAuth is properly configured and enabled."""
        return (
            settings.GOOGLE_OAUTH_ENABLED and
            self.client_id != "your-google-client-id" and
            self.client_secret != "your-google-client-secret" and
            self.redirect_uri != "your-google-redirect-uri"
        )