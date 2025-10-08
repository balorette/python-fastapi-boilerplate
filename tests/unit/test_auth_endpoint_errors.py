"""Additional coverage for error branches in app.api.v1.endpoints.auth."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ValidationError as AppValidationError,
)
from app.schemas.oauth import AuthorizationRequest, TokenRequest


@pytest.mark.asyncio
async def test_authorize_local_requires_credentials(monkeypatch) -> None:
    """Local authorization should reject requests without credentials."""

    class DummyAuthService:
        def __init__(self, *_args, **_kwargs) -> None:  # pragma: no cover - simple stub
            pass

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", DummyAuthService
    )

    from app.api.v1.endpoints.auth import authorize

    request = AuthorizationRequest(
        provider="local",
        client_id="client",
        redirect_uri="https://client.example.com/callback",
        state="state-123",
    )

    with pytest.raises(HTTPException) as exc:
        await authorize(request, AsyncMock())

    assert exc.value.status_code == 400
    assert "Username and password required" in exc.value.detail


@pytest.mark.asyncio
async def test_authorize_local_authorization_error(monkeypatch) -> None:
    """Authorization errors should translate to HTTP 403 responses."""

    class DummyAuthService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        async def authorize_local(self, *_args, **_kwargs):
            raise AuthorizationError("forbidden")

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", DummyAuthService
    )

    from app.api.v1.endpoints.auth import authorize

    request = AuthorizationRequest(
        provider="local",
        client_id="client",
        redirect_uri="https://client.example.com/callback",
        state="state-123",
        username="user@example.com",
        password="secret",
    )

    with pytest.raises(HTTPException) as exc:
        await authorize(request, AsyncMock())

    assert exc.value.status_code == 403
    assert "forbidden" in exc.value.detail


@pytest.mark.asyncio
async def test_authorize_local_app_validation_error(monkeypatch) -> None:
    """Pydantic-style validation errors should map to HTTP 400."""

    class FailingAuthService:
        def __init__(self, *_args, **_kwargs) -> None:
            raise AppValidationError("invalid payload")

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", FailingAuthService
    )

    from app.api.v1.endpoints.auth import authorize

    request = AuthorizationRequest(
        provider="local",
        client_id="client",
        redirect_uri="https://client.example.com/callback",
        state="state-123",
    )

    with pytest.raises(HTTPException) as exc:
        await authorize(request, AsyncMock())

    assert exc.value.status_code == 400
    assert "invalid payload" in exc.value.detail


@pytest.mark.asyncio
async def test_authorize_local_generic_error(monkeypatch) -> None:
    """Unexpected errors should surface as HTTP 500 responses."""

    class FailingAuthService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        async def authorize_local(self, *_args, **_kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", FailingAuthService
    )

    from app.api.v1.endpoints.auth import authorize

    request = AuthorizationRequest(
        provider="local",
        client_id="client",
        redirect_uri="https://client.example.com/callback",
        state="state-123",
        username="user@example.com",
        password="secret",
    )

    with pytest.raises(HTTPException) as exc:
        await authorize(request, AsyncMock())

    assert exc.value.status_code == 500
    assert "Authorization failed" in exc.value.detail


@pytest.mark.asyncio
async def test_token_external_missing_access_token(
    monkeypatch, oauth_provider_stub, patch_oauth_provider_factory
) -> None:
    """Token endpoint should guard against providers omitting access tokens."""

    oauth_provider_stub.tokens_response = {"refresh_token": "remote-refresh"}
    patch_oauth_provider_factory(oauth_provider_stub)

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", lambda *_args, **_kwargs: AsyncMock()
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="google",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 502
    assert "did not return an access token" in exc.value.detail


@pytest.mark.asyncio
async def test_token_local_exchange_authentication_error(monkeypatch) -> None:
    """Local token exchange failures should respond with HTTP 400."""

    class DummyAuthService:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        async def exchange_local_authorization_code(self, *_args, **_kwargs):
            raise AuthenticationError("bad code")

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", DummyAuthService
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="local",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 400
    assert "bad code" in exc.value.detail


@pytest.mark.asyncio
async def test_token_external_invalid_id_token(
    monkeypatch, oauth_provider_stub, patch_oauth_provider_factory
) -> None:
    """Invalid ID tokens from the provider should bubble up as HTTP 401."""

    async def raise_invalid_id(*_args, **_kwargs):
        raise AuthenticationError("bad id token")

    oauth_provider_stub.tokens_response = {
        "access_token": "remote-access",
        "refresh_token": "remote-refresh",
        "id_token": "bad-token",
    }
    oauth_provider_stub.user_info_response = {
        "id": "user-id",
        "email": "oauth@example.com",
        "verified_email": True,
        "name": "OAuth User",
        "given_name": "OAuth",
        "family_name": "User",
        "picture": None,
        "locale": "en-US",
    }
    oauth_provider_stub.validate_id_token = raise_invalid_id
    patch_oauth_provider_factory(oauth_provider_stub)

    async def fake_create_or_update(
        self, google_user_info, refresh_token=None
    ) -> tuple[SimpleNamespace, bool]:
        user = SimpleNamespace(
            id=42,
            email=google_user_info.email,
            username="oauth-user",
            full_name=google_user_info.name,
        )
        return user, False

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", lambda *_args, **_kwargs: AsyncMock()
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.UserService.create_or_update_oauth_user",
        fake_create_or_update,
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="google",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 401
    assert "Invalid ID token" in exc.value.detail


@pytest.mark.asyncio
async def test_token_external_user_info_failure(
    monkeypatch, oauth_provider_stub, patch_oauth_provider_factory
) -> None:
    """Provider user info failures should map to HTTP 401."""

    async def fail_user_info(*_args, **_kwargs):
        raise AuthenticationError("no profile")

    oauth_provider_stub.tokens_response = {"access_token": "token"}
    oauth_provider_stub.get_user_info = fail_user_info
    patch_oauth_provider_factory(oauth_provider_stub)

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", lambda *_args, **_kwargs: AsyncMock()
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="google",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 401
    assert "Failed to fetch user info" in exc.value.detail


@pytest.mark.asyncio
async def test_token_external_invalid_user_info(monkeypatch, oauth_provider_stub, patch_oauth_provider_factory) -> None:
    """Malformed provider payloads should return HTTP 502."""

    oauth_provider_stub.tokens_response = {"access_token": "token"}
    oauth_provider_stub.user_info_response = {"id": "missing-email"}
    patch_oauth_provider_factory(oauth_provider_stub)

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", lambda *_args, **_kwargs: AsyncMock()
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="google",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 502
    assert "Invalid user info from Google" in exc.value.detail


@pytest.mark.asyncio
async def test_token_external_provider_not_implemented(
    monkeypatch, oauth_provider_stub, patch_oauth_provider_factory
) -> None:
    """Non-Google providers should return HTTP 501 until implemented."""

    oauth_provider_stub.tokens_response = {"access_token": "token"}
    oauth_provider_stub.user_info_response = {
        "id": "provider-id",
        "email": "user@example.com",
        "verified_email": True,
        "name": "Other Provider",
        "given_name": "Other",
        "family_name": "Provider",
        "picture": None,
        "locale": "en-US",
    }
    patch_oauth_provider_factory(oauth_provider_stub)

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", lambda *_args, **_kwargs: AsyncMock()
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="entra",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 501
    assert "not implemented" in exc.value.detail


@pytest.mark.asyncio
async def test_token_generic_error(monkeypatch) -> None:
    """Unexpected exceptions should surface as HTTP 500 responses."""

    def raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("factory exploded")

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.AuthService", lambda *_args, **_kwargs: AsyncMock()
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.OAuthProviderFactory.create_provider",
        classmethod(lambda cls, provider: raise_runtime_error()),
    )

    from app.api.v1.endpoints.auth import token

    request = TokenRequest(
        provider="google",
        grant_type="authorization_code",
        code="auth-code",
        redirect_uri="https://client.example.com/callback",
        client_id="client",
    )

    with pytest.raises(HTTPException) as exc:
        await token(request, AsyncMock())

    assert exc.value.status_code == 500
    assert "Token exchange failed" in exc.value.detail


@pytest.mark.asyncio
async def test_oauth_callback_error(monkeypatch) -> None:
    """Callback should return 400 when provider reports an error."""

    from app.api.v1.endpoints.auth import oauth_callback

    with pytest.raises(HTTPException) as exc:
        await oauth_callback("google", "code", error="access_denied", db=AsyncMock())

    assert exc.value.status_code == 400
    assert "OAuth authorization failed" in exc.value.detail


@pytest.mark.asyncio
async def test_oauth_callback_success_includes_state(monkeypatch) -> None:
    """Callback should redirect with provider, code, and state parameters."""

    from app.api.v1.endpoints.auth import oauth_callback

    response = await oauth_callback("google", "code-123", state="xyz", db=AsyncMock())

    assert response.status_code in {302, 307}
    assert "code=code-123" in str(response.headers["location"]).lower()
    assert "state=xyz" in response.headers["location"]


@pytest.mark.asyncio
async def test_revoke_token_handles_invalid_token(monkeypatch) -> None:
    """Revocation endpoint should swallow verification errors."""

    def raise_error(_token: str) -> None:
        raise ValueError("bad token")

    monkeypatch.setattr("app.api.v1.endpoints.auth.verify_token", raise_error)

    from app.api.v1.endpoints.auth import revoke_token

    result = await revoke_token("not-a-token", AsyncMock())
    assert result == {"message": "Token revoked successfully"}
