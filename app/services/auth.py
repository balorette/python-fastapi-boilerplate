"""Authentication service orchestrating login and token workflows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.schemas.oauth import (
    AuthorizationResponse,
    LocalLoginRequest,
    TokenResponse,
)
from app.services.user import UserService


settings = get_settings()


class AuthService:
    """Provide reusable authentication flows for FastAPI endpoints."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_service = UserService(session)
        self.repository = self.user_service.repository

    async def authorize_local(
        self,
        *,
        username_or_email: str,
        password: str,
        state: str,
        redirect_uri: str,
    ) -> AuthorizationResponse:
        """Validate local credentials and mint a short-lived auth code."""

        user = await self.user_service.authenticate_user(username_or_email, password)

        authorization_code = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "type": "auth_code",
            },
            expires_delta_minutes=10,
        )

        return AuthorizationResponse(
            authorization_code=authorization_code,
            authorization_url=None,
            state=state,
            redirect_uri=redirect_uri,
            code_verifier=None,
        )

    async def exchange_local_authorization_code(self, code: str) -> TokenResponse:
        """Turn a validated auth code into access and refresh tokens."""

        payload = verify_token(code)
        if not payload or payload.get("type") != "auth_code":
            raise AuthenticationError("Invalid authorization code")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Authorization code missing subject")

        user = await self.repository.get(int(user_id))
        if not user:
            raise AuthenticationError("User not found")

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "name": user.full_name or user.username,
                "provider": "local",
            }
        )

        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            scope="openid email profile",
            user_id=user.id,
            email=user.email,
            username=user.username,
            is_new_user=False,
        )

    async def login_local(self, request: LocalLoginRequest) -> TokenResponse:
        """Authenticate a local user and update their last_login timestamp."""

        user = await self.user_service.authenticate_user(request.email, request.password)

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "name": user.full_name or user.username,
                "provider": "local",
            }
        )

        refresh_token = create_refresh_token(user.id)

        await self.repository.update(user, {"last_login": datetime.now(UTC)})

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            scope="openid email profile",
            user_id=user.id,
            email=user.email,
            username=user.username,
            is_new_user=False,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Rotate access and refresh tokens for an active user."""

        payload = verify_token(refresh_token, "refresh_token")
        if not payload:
            raise AuthenticationError("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Refresh token missing subject")

        user = await self.repository.get(int(user_id))
        if not user or not getattr(user, "is_active", False):
            raise AuthenticationError("User not found or inactive")

        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "name": user.full_name or user.username,
                "provider": getattr(user, "oauth_provider", "local"),
            }
        )

        rotated_refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=rotated_refresh_token,
            scope="openid email profile",
            user_id=user.id,
            email=user.email,
            username=user.username,
            is_new_user=False,
        )
