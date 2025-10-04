"""Real OAuth2 authentication tests aligned with the provider/factory flow."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.core.security import create_access_token, verify_token
from app.models.user import User


class TestOAuth2RealAuth:
    """Exercise key authentication scenarios against the FastAPI app."""

    async def test_oauth_login_success_with_real_jwt(
        self, client_with_real_db, sample_user_in_db
    ):
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_in_db.email,
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )
        assert response.status_code == 200
        token_data = response.json()
        assert token_data["user_id"] == sample_user_in_db.id
        assert token_data["email"] == sample_user_in_db.email
        assert token_data["username"] == sample_user_in_db.username
        payload = verify_token(token_data["access_token"])
        assert payload is not None and payload["sub"] == str(sample_user_in_db.id)

    async def test_oauth_login_invalid_credentials(self, client_with_real_db):
        response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123!",
                "grant_type": "password",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_protected_endpoint_with_real_jwt_validation(self, client: TestClient):
        now = datetime.now(timezone.utc)
        test_user = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            "hashed_password": "not-used",
            "created_at": now,
            "updated_at": now,
        }
        access_token = create_access_token(
            {"sub": str(test_user["id"]), "email": test_user["email"]}
        )
        with patch("app.services.user.UserService.get_user") as mock_get_user:
            mock_get_user.return_value = User(**test_user)
            response = client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == test_user["id"]
        assert payload["email"] == test_user["email"]

    def test_invalid_jwt_token_validation(self, client: TestClient):
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401

    def test_expired_jwt_token(self, client: TestClient):
        from datetime import timedelta

        token = create_access_token(
            data={"sub": "1", "email": "test@example.com"},
            expires_delta=timedelta(seconds=-1),
        )
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    async def test_refresh_token_flow(self, client_with_real_db, sample_user_in_db):
        login_response = client_with_real_db.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user_in_db.email,
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        refresh_response = client_with_real_db.post(
            "/api/v1/auth/refresh",
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        assert refresh_response.status_code == 200
        refreshed = refresh_response.json()
        assert refreshed["user_id"] == sample_user_in_db.id
        assert refreshed["access_token"] != login_response.json()["access_token"]

    async def test_user_deactivation_blocks_access(
        self, client_with_real_db, sample_user_in_db, async_db_session
    ):
        token = create_access_token(
            {"sub": str(sample_user_in_db.id), "email": sample_user_in_db.email}
        )
        headers = {"Authorization": f"Bearer {token}"}
        assert (
            client_with_real_db.get("/api/v1/users/me", headers=headers).status_code
            == 200
        )
        sample_user_in_db.is_active = False
        async_db_session.add(sample_user_in_db)
        await async_db_session.commit()
        forbidden = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert forbidden.status_code in (401, 403)

    def test_jwt_token_with_invalid_user_id(self, client: TestClient):
        token = create_access_token({"sub": "99999", "email": "ghost@example.com"})
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_oauth_login_validation_errors(self, client: TestClient):
        assert client.post("/api/v1/auth/login", json={}).status_code in (400, 422)
        assert client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "grant_type": "password"},
        ).status_code in (400, 422)
        assert client.post(
            "/api/v1/auth/login",
            json={
                "email": "invalid-email",
                "password": "TestPass123!",
                "grant_type": "password",
            },
        ).status_code in (400, 422)

    def test_concurrent_token_usage(self, client: TestClient):
        current = datetime.now(timezone.utc)
        user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_superuser": False,
            "hashed_password": "not-used",
            "created_at": current,
            "updated_at": current,
        }
        token = create_access_token(
            {"sub": str(user_data["id"]), "email": user_data["email"]}
        )
        with patch("app.services.user.UserService.get_user") as mock_get_user:
            mock_get_user.return_value = User(**user_data)
            headers = {"Authorization": f"Bearer {token}"}
            resp1 = client.get("/api/v1/users/me", headers=headers)
            resp2 = client.get("/api/v1/users/me", headers=headers)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["id"] == resp2.json()["id"]

    @patch("app.services.oauth.factory.OAuthProviderFactory.create_provider")
    async def test_google_oauth_token_exchange_flow(
        self,
        mock_create_provider,
        client_with_real_db,
        async_db_session,
    ):
        provider_mock = AsyncMock()
        provider_mock.exchange_code_for_tokens.return_value = {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "scope": "openid email profile",
            "id_token": "google-id-token",
        }
        provider_mock.get_user_info.return_value = {
            "id": "google_user_123456",
            "email": "googleuser@gmail.com",
            "verified_email": True,
            "name": "Google Test User",
            "given_name": "Google",
            "family_name": "User",
            "picture": "https://example.com/picture.jpg",
            "locale": "en-US",
        }
        provider_mock.validate_id_token.return_value = {
            "sub": "google_user_123456",
            "email": "googleuser@gmail.com",
            "name": "Google Test User",
            "email_verified": True,
        }
        mock_create_provider.return_value = provider_mock

        token_response = client_with_real_db.post(
            "/api/v1/auth/token",
            json={
                "provider": "google",
                "grant_type": "authorization_code",
                "code": "mock_google_auth_code",
                "redirect_uri": "http://localhost:8000/api/v1/auth/callback/google",
            },
        )
        assert token_response.status_code == 200
        token_data = token_response.json()
        assert token_data["email"] == "googleuser@gmail.com"
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        me_response = client_with_real_db.get("/api/v1/users/me", headers=headers)
        assert me_response.status_code == 200
        user_service_response = me_response.json()
        assert user_service_response["email"] == "googleuser@gmail.com"
