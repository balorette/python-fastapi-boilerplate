"""Base OAuth provider interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseOAuthProvider(ABC):
    """Abstract base class for OAuth providers."""

    @abstractmethod
    async def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scope: str | None = None,
        code_challenge: str | None = None
    ) -> str:
        """Generate OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        pass

    @abstractmethod
    async def validate_id_token(self, id_token: str) -> dict[str, Any]:
        """Validate and decode ID token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from provider."""
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token using refresh token."""
        pass
