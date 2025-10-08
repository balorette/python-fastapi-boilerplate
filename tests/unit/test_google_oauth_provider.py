"""Unit tests for the Google OAuth provider and factory helpers."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core.exceptions import AuthenticationError, ValidationError
from app.services.oauth.base import BaseOAuthProvider
from app.services.oauth.factory import OAuthProviderFactory
from app.services.oauth.google import GoogleOAuthProvider

ORIGINAL_PROVIDERS = OAuthProviderFactory._providers.copy()


class StubResponse:
    """Minimal HTTPX response stub with configurable behaviour."""

    def __init__(
        self, json_data: dict[str, Any] | None = None, *, text: str = ""
    ) -> None:
        self._json = json_data or {}
        self.text = text
        self._raise_exc: httpx.HTTPStatusError | None = None

    def set_http_error(self, status_code: int, method: str = "POST") -> None:
        request = httpx.Request(method, "https://example.com")
        response = httpx.Response(status_code, request=request, text=self.text)
        self._raise_exc = httpx.HTTPStatusError(
            self.text or "error", request=request, response=response
        )

    def raise_for_status(self) -> None:
        if self._raise_exc:
            raise self._raise_exc

    def json(self) -> dict[str, Any]:
        return self._json


class AsyncClientStub:
    """Context manager stub that returns preconfigured responses."""

    def __init__(
        self,
        *,
        post_response: StubResponse | None = None,
        get_response: StubResponse | None = None,
        post_exception: Exception | None = None,
        get_exception: Exception | None = None,
    ) -> None:
        self.post_response = post_response
        self.get_response = get_response
        self.post_exception = post_exception
        self.get_exception = get_exception
        self.post_calls: list[tuple[str, dict[str, Any] | None]] = []
        self.get_calls: list[tuple[str, dict[str, str] | None]] = []

    async def __aenter__(self) -> AsyncClientStub:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, url: str, data: dict[str, Any] | None = None) -> StubResponse:
        self.post_calls.append((url, data))
        if self.post_exception:
            raise self.post_exception
        assert self.post_response is not None
        return self.post_response

    async def get(
        self, url: str, headers: dict[str, str] | None = None
    ) -> StubResponse:
        self.get_calls.append((url, headers))
        if self.get_exception:
            raise self.get_exception
        assert self.get_response is not None
        return self.get_response


@pytest.fixture(autouse=True)
def reset_oauth_factory(monkeypatch) -> None:
    """Ensure each test operates on a clean provider registry."""

    monkeypatch.setattr(
        OAuthProviderFactory, "_providers", ORIGINAL_PROVIDERS.copy(), raising=False
    )


@pytest.mark.asyncio
async def test_get_authorization_url_includes_pkce() -> None:
    """Authorization URLs should include PKCE parameters when provided."""

    provider = GoogleOAuthProvider()
    url = await provider.get_authorization_url(
        redirect_uri="https://client.example.com/callback",
        state="state-123",
        scope="openid email",
        code_challenge="challenge-value",
    )

    assert "code_challenge=challenge-value" in url
    assert "code_challenge_method=S256" in url
    assert "state=state-123" in url


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_success(monkeypatch) -> None:
    """Successful token exchange should return provider payload."""

    provider = GoogleOAuthProvider()
    response = StubResponse({"access_token": "abc", "refresh_token": "def"})
    client_stub = AsyncClientStub(post_response=response)
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    tokens = await provider.exchange_code_for_tokens(
        "auth-code", "https://client.example.com/callback"
    )

    assert tokens["access_token"] == "abc"
    assert client_stub.post_calls[0][0] == provider.token_uri


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_http_error(monkeypatch) -> None:
    """HTTP errors should be wrapped as AuthenticationError."""

    provider = GoogleOAuthProvider()
    response = StubResponse(text="invalid grant")
    response.set_http_error(400)
    client_stub = AsyncClientStub(post_response=response)
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.exchange_code_for_tokens(
            "bad-code", "https://client.example.com/callback"
        )
    assert "Token exchange failed" in str(exc.value)


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_generic_error(monkeypatch) -> None:
    """Unexpected errors from httpx should also map to AuthenticationError."""

    provider = GoogleOAuthProvider()
    client_stub = AsyncClientStub(post_exception=RuntimeError("boom"))
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.exchange_code_for_tokens(
            "code", "https://client.example.com/callback"
        )
    assert "Token exchange error" in str(exc.value)


@pytest.mark.asyncio
async def test_get_user_info_success(monkeypatch) -> None:
    """User info requests should return JSON payloads from Google."""

    provider = GoogleOAuthProvider()
    response = StubResponse({"email": "user@example.com"})
    client_stub = AsyncClientStub(get_response=response)
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    data = await provider.get_user_info("access-token")

    assert data["email"] == "user@example.com"
    assert client_stub.get_calls[0][0] == provider.userinfo_uri
    headers = client_stub.get_calls[0][1]
    assert headers is not None
    assert headers["Authorization"].startswith("Bearer ")


@pytest.mark.asyncio
async def test_get_user_info_http_error(monkeypatch) -> None:
    """HTTP failures during user info retrieval should raise AuthenticationError."""

    provider = GoogleOAuthProvider()
    response = StubResponse(text="not authorised")
    response.set_http_error(401, method="GET")
    client_stub = AsyncClientStub(get_response=response)
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.get_user_info("bad-token")
    assert "Failed to get user info" in str(exc.value)


@pytest.mark.asyncio
async def test_get_user_info_generic_error(monkeypatch) -> None:
    """Unexpected user info errors should also map to AuthenticationError."""

    provider = GoogleOAuthProvider()
    client_stub = AsyncClientStub(get_exception=RuntimeError("boom"))
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.get_user_info("token")
    assert "User info error" in str(exc.value)


@pytest.mark.asyncio
async def test_refresh_access_token_success(monkeypatch) -> None:
    """Refresh token requests should proxy Google's response."""

    provider = GoogleOAuthProvider()
    response = StubResponse({"access_token": "new-token"})
    client_stub = AsyncClientStub(post_response=response)
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    refreshed = await provider.refresh_access_token("refresh-token")

    assert refreshed["access_token"] == "new-token"
    assert client_stub.post_calls[0][0] == provider.token_uri


@pytest.mark.asyncio
async def test_refresh_access_token_http_error(monkeypatch) -> None:
    """Errors during refresh should bubble up as AuthenticationError."""

    provider = GoogleOAuthProvider()
    response = StubResponse(text="expired refresh")
    response.set_http_error(400)
    client_stub = AsyncClientStub(post_response=response)
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.refresh_access_token("stale-token")
    assert "Token refresh failed" in str(exc.value)


@pytest.mark.asyncio
async def test_refresh_access_token_generic_error(monkeypatch) -> None:
    """Unexpected refresh errors should raise AuthenticationError."""

    provider = GoogleOAuthProvider()
    client_stub = AsyncClientStub(post_exception=RuntimeError("boom"))
    monkeypatch.setattr(
        "app.services.oauth.google.httpx.AsyncClient",
        lambda *args, **kwargs: client_stub,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.refresh_access_token("token")
    assert "Token refresh error" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_id_token_success(monkeypatch) -> None:
    """ID token validation should return Google's decoded payload."""

    provider = GoogleOAuthProvider()

    class DummyLoop:
        async def run_in_executor(self, _executor, func, *args, **kwargs):
            return func()

    monkeypatch.setattr(
        "app.services.oauth.google.asyncio.get_event_loop",
        lambda: DummyLoop(),
    )
    monkeypatch.setattr(
        "app.services.oauth.google.id_token.verify_oauth2_token",
        lambda token, request, client_id: {"sub": "123"},
    )

    payload = await provider.validate_id_token("token-value")
    assert payload["sub"] == "123"


@pytest.mark.asyncio
async def test_validate_id_token_invalid(monkeypatch) -> None:
    """Value errors from Google's verifier should surface as AuthenticationError."""

    provider = GoogleOAuthProvider()

    class DummyLoop:
        async def run_in_executor(self, _executor, func, *args, **kwargs):
            return func()

    monkeypatch.setattr(
        "app.services.oauth.google.asyncio.get_event_loop",
        lambda: DummyLoop(),
    )

    def raise_value_error(*_args, **_kwargs):
        raise ValueError("bad token")

    monkeypatch.setattr(
        "app.services.oauth.google.id_token.verify_oauth2_token",
        raise_value_error,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.validate_id_token("token-value")
    assert "Invalid ID token" in str(exc.value)


@pytest.mark.asyncio
async def test_validate_id_token_other_error(monkeypatch) -> None:
    """Unexpected validation errors should also map to AuthenticationError."""

    provider = GoogleOAuthProvider()

    class DummyLoop:
        async def run_in_executor(self, _executor, func, *args, **kwargs):
            return func()

    monkeypatch.setattr(
        "app.services.oauth.google.asyncio.get_event_loop",
        lambda: DummyLoop(),
    )

    def raise_runtime_error(*_args, **_kwargs):
        raise RuntimeError("oops")

    monkeypatch.setattr(
        "app.services.oauth.google.id_token.verify_oauth2_token",
        raise_runtime_error,
    )

    with pytest.raises(AuthenticationError) as exc:
        await provider.validate_id_token("token-value")
    assert "ID token validation error" in str(exc.value)


def test_factory_unknown_provider_raises() -> None:
    """Unsupported providers should raise ValidationError."""

    with pytest.raises(ValidationError):
        OAuthProviderFactory.create_provider("unknown")


def test_factory_register_provider_creates_instance() -> None:
    """Registering a custom provider should allow instantiation via the factory."""

    class DummyProvider(BaseOAuthProvider):
        async def get_authorization_url(
            self,
            redirect_uri: str,
            state: str,
            scope: str | None = None,
            code_challenge: str | None = None,
        ) -> str:
            return f"{redirect_uri}?state={state}"

        async def exchange_code_for_tokens(
            self, code: str, redirect_uri: str, code_verifier: str | None = None
        ) -> dict[str, Any]:
            return {"code": code, "redirect_uri": redirect_uri}

        async def validate_id_token(self, id_token: str) -> dict[str, Any]:
            return {"token": id_token}

        async def get_user_info(self, access_token: str) -> dict[str, Any]:
            return {"token": access_token}

        async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
            return {"token": refresh_token}

    OAuthProviderFactory.register_provider("dummy", DummyProvider)
    provider = OAuthProviderFactory.create_provider("dummy")

    assert isinstance(provider, DummyProvider)
    assert "dummy" in OAuthProviderFactory.get_supported_providers()
