"""Unit tests for the authentication service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.schemas.oauth import LocalLoginRequest
from app.services.auth import AuthService


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def auth_service(mock_session) -> AuthService:
    service = AuthService(mock_session)
    return service


@pytest.fixture
def sample_user() -> User:
    now = datetime.now(UTC)
    return User(
        id=42,
        username="tester",
        email="tester@example.com",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        hashed_password="hashed",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_authorize_local_success(auth_service: AuthService, sample_user: User) -> None:
    auth_service.user_service.authenticate_user = AsyncMock(return_value=sample_user)

    with patch("app.services.auth.create_access_token", return_value="auth-code"):
        response = await auth_service.authorize_local(
            username_or_email=sample_user.email,
            password="password",
            state="state123",
            redirect_uri="https://example.com/callback",
        )

    assert response.authorization_code == "auth-code"
    assert response.state == "state123"


@pytest.mark.asyncio
async def test_exchange_local_authorization_code_success(
    auth_service: AuthService,
    sample_user: User,
) -> None:
    auth_service.repository.get = AsyncMock(return_value=sample_user)

    with patch("app.services.auth.verify_token", return_value={"sub": str(sample_user.id), "type": "auth_code"}):
        with patch("app.services.auth.create_access_token", return_value="access"):
            with patch("app.services.auth.create_refresh_token", return_value="refresh"):
                token = await auth_service.exchange_local_authorization_code("code")

    assert token.access_token == "access"
    assert token.refresh_token == "refresh"
    assert token.user_id == sample_user.id


@pytest.mark.asyncio
async def test_exchange_local_authorization_code_invalid(auth_service: AuthService) -> None:
    with patch("app.services.auth.verify_token", return_value=None):
        with pytest.raises(AuthenticationError):
            await auth_service.exchange_local_authorization_code("invalid")


@pytest.mark.asyncio
async def test_login_local_updates_last_login(
    auth_service: AuthService,
    sample_user: User,
) -> None:
    auth_service.user_service.authenticate_user = AsyncMock(return_value=sample_user)
    auth_service.repository.update = AsyncMock()

    with patch("app.services.auth.create_access_token", return_value="access"):
        with patch("app.services.auth.create_refresh_token", return_value="refresh"):
            response = await auth_service.login_local(
                LocalLoginRequest(email=sample_user.email, password="password")
            )

    auth_service.repository.update.assert_awaited()
    assert response.access_token == "access"


@pytest.mark.asyncio
async def test_refresh_tokens_success(auth_service: AuthService, sample_user: User) -> None:
    auth_service.repository.get = AsyncMock(return_value=sample_user)

    with patch("app.services.auth.verify_token", return_value={"sub": str(sample_user.id)}):
        with patch("app.services.auth.create_access_token", return_value="access"):
            with patch("app.services.auth.create_refresh_token", return_value="rotated"):
                tokens = await auth_service.refresh_tokens("refresh-token")

    assert tokens.refresh_token == "rotated"
    assert tokens.user_id == sample_user.id


@pytest.mark.asyncio
async def test_refresh_tokens_inactive_user(auth_service: AuthService, sample_user: User) -> None:
    inactive_user = sample_user
    inactive_user.is_active = False
    auth_service.repository.get = AsyncMock(return_value=inactive_user)

    with patch("app.services.auth.verify_token", return_value={"sub": str(sample_user.id)}):
        with pytest.raises(AuthenticationError):
            await auth_service.refresh_tokens("refresh-token")
