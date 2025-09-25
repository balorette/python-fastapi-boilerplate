"""Google OAuth provider implementation."""

import asyncio
from typing import Any
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.services.oauth.base import BaseOAuthProvider


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth 2.0 provider implementation."""

    def __init__(self):
        """Initialize Google OAuth provider."""
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.auth_uri = "https://accounts.google.com/o/oauth2/auth"
        self.token_uri = "https://oauth2.googleapis.com/token"
        self.userinfo_uri = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.scopes = [
            "openid",
            "profile",
            "email"
        ]

    async def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scope: str | None = None,
        code_challenge: str | None = None
    ) -> str:
        """Generate Google OAuth authorization URL with PKCE support."""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": scope or " ".join(self.scopes),
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "state": state,
        }

        # Add PKCE parameters if provided
        if code_challenge:
            params.update({
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            })

        return f"{self.auth_uri}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None
    ) -> dict[str, Any]:
        """Exchange authorization code for access tokens."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        # Add PKCE verifier if provided
        if code_verifier:
            data["code_verifier"] = code_verifier

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_uri, data=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(f"Token exchange failed: {e.response.text}")
            except Exception as e:
                raise AuthenticationError(f"Token exchange error: {str(e)}")

    async def validate_id_token(self, id_token_str: str) -> dict[str, Any]:
        """Validate Google ID token using Google's public keys."""
        try:
            # Use asyncio to run the sync validation in a thread
            def _validate():
                return id_token.verify_oauth2_token(
                    id_token_str,
                    google_requests.Request(),
                    self.client_id
                )

            loop = asyncio.get_event_loop()
            id_info = await loop.run_in_executor(None, _validate)

            return id_info

        except ValueError as e:
            raise AuthenticationError(f"Invalid ID token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"ID token validation error: {str(e)}")

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Google's userinfo endpoint."""
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.userinfo_uri, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(f"Failed to get user info: {e.response.text}")
            except Exception as e:
                raise AuthenticationError(f"User info error: {str(e)}")

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh Google access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_uri, data=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise AuthenticationError(f"Token refresh failed: {e.response.text}")
            except Exception as e:
                raise AuthenticationError(f"Token refresh error: {str(e)}")
