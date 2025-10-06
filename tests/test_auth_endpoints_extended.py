"""Additional coverage for auth endpoints covering OAuth flows."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import auth as auth_module
from app.schemas.user import UserCreate
from app.services.user import UserService


async def _create_active_user(async_db_session: AsyncSession) -> tuple[str, str]:
    """Create and commit an active test user returning (username, password)."""
    unique = uuid.uuid4().hex[:8]
    password = "StrongPass123!"
    user_data = UserCreate(
        username=f"authflow_{unique}",
        email=f"authflow_{unique}@example.com",
        password=password,
        confirm_password=password,
        full_name="Auth Flow Tester",
        is_active=True,
        is_superuser=False,
    )
    user_service = UserService(async_db_session)
    await user_service.create_user(user_data)
    await async_db_session.commit()
    return user_data.username, password


async def test_authorize_local_flow_returns_tokens(
    client_with_db: TestClient,
    async_db_session: AsyncSession,
) -> None:
    """Full local OAuth code flow should return usable tokens."""
    username, password = await _create_active_user(async_db_session)

    authorize_payload = {
        "provider": "local",
        "client_id": "test-client",
        "redirect_uri": "https://client.example.com/callback",
        "scope": "openid email profile",
        "state": "state-token",
        "username": username,
        "password": password,
    }

    authorize_response = client_with_db.post(
        "/api/v1/auth/authorize",
        json=authorize_payload,
    )
    assert authorize_response.status_code == 200
    authorize_data = authorize_response.json()
    assert authorize_data["authorization_code"]

    token_payload = {
        "provider": "local",
        "grant_type": "authorization_code",
        "code": authorize_data["authorization_code"],
        "client_id": "test-client",
        "redirect_uri": "https://client.example.com/callback",
    }

    token_response = client_with_db.post(
        "/api/v1/auth/token",
        json=token_payload,
    )
    assert token_response.status_code == 200
    token_data = token_response.json()
    assert token_data["token_type"] == "Bearer"
    assert token_data["scope"] == "openid email profile"
    assert token_data["refresh_token"]


def test_authorize_google_requires_redirect(
    client_with_db: TestClient,
    monkeypatch,
) -> None:
    """Google auth must fail fast when redirect URI is unavailable."""
    monkeypatch.setattr(auth_module.settings, "GOOGLE_REDIRECT_URI", "")

    response = client_with_db.post(
        "/api/v1/auth/authorize",
        json={
            "provider": "google",
            "client_id": "test-client",
            "redirect_uri": "",
            "scope": "openid email",
            "state": "missing-redirect",
        },
    )

    assert response.status_code == 400
    assert "Redirect URI is required" in response.json()["detail"]


def test_authorize_google_returns_redirect(
    client_with_db: TestClient,
    patch_oauth_provider_factory,
    oauth_provider_stub,
) -> None:
    """External provider should return authorization URL with defaults."""

    oauth_provider_stub.authorization_url = "https://auth.example.com/oauth"
    patch_oauth_provider_factory(oauth_provider_stub)

    response = client_with_db.post(
        "/api/v1/auth/authorize",
        json={
            "provider": "google",
            "client_id": "test-client",
            "redirect_uri": "https://client.example.com/callback",
            "scope": "openid email",
            "state": "state-123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["authorization_url"] == "https://auth.example.com/oauth"
    assert data["authorization_code"] is None


def test_token_rejects_unsupported_grant(client_with_db: TestClient) -> None:
    """Only authorization_code grant should be accepted by /token."""
    response = client_with_db.post(
        "/api/v1/auth/token",
        json={
            "provider": "local",
            "grant_type": "refresh_token",
            "refresh_token": "dummy-refresh",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported grant type"


def test_token_requires_authorization_code(client_with_db: TestClient) -> None:
    """Token exchange should guard against missing authorization codes."""
    response = client_with_db.post(
        "/api/v1/auth/token",
        json={
            "provider": "local",
            "grant_type": "authorization_code",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Authorization code is required"


async def test_token_google_flow_returns_tokens(
    client_with_db: TestClient,
    monkeypatch,
    patch_oauth_provider_factory,
    oauth_provider_stub,
) -> None:
    """Google token exchange path should mint local tokens when provider succeeds."""

    async def fake_create_or_update(
        self,
        google_user_info,
        refresh_token=None,
    ) -> tuple[SimpleNamespace, bool]:  # type: ignore[override]
        user = SimpleNamespace(
            id=777,
            email=google_user_info.email,
            username="oauth-user",
            full_name=google_user_info.name,
        )
        return user, True

    oauth_provider_stub.tokens_response = {
        "access_token": "remote-access",
        "refresh_token": "remote-refresh",
        "scope": "openid email profile",
        "id_token": "remote-id",
    }
    oauth_provider_stub.user_info_response = {
        "id": "google-id",
        "email": "oauth@example.com",
        "verified_email": True,
        "name": "OAuth Example",
        "given_name": "OAuth",
        "family_name": "Example",
        "picture": None,
        "locale": "en-US",
    }
    oauth_provider_stub.id_info_response = {"sub": "google-id"}
    patch_oauth_provider_factory(oauth_provider_stub)
    monkeypatch.setattr(
        auth_module.UserService,
        "create_or_update_oauth_user",
        fake_create_or_update,
    )

    response = client_with_db.post(
        "/api/v1/auth/token",
        json={
            "provider": "google",
            "grant_type": "authorization_code",
            "code": "dummy-code",
            "client_id": "test-client",
            "redirect_uri": "https://client.example.com/callback",
            "code_verifier": "code-verifier",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 777
    assert data["email"] == "oauth@example.com"
    assert data["is_new_user"] is True
    assert data["refresh_token"]
