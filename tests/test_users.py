"""Test user management endpoints with RBAC-aware expectations."""

from fastapi.testclient import TestClient


def _assert_has_member_role(user_payload: dict) -> None:
    assert "roles" in user_payload
    assert any(role["name"] == "member" for role in user_payload["roles"])


def test_get_users(client: TestClient, auth_headers: dict) -> None:
    """Admins can retrieve a paginated list of users including role data."""

    response = client.get("/api/v1/users/", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["items"], list)
    assert all("roles" in user for user in data["items"])


def test_get_user_by_id(client: TestClient, auth_headers: dict) -> None:
    """Admins can retrieve a single user and see assigned roles."""

    user_payload = {
        "email": "gettest@example.com",
        "username": "getuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Get Test User",
        "is_active": True,
        "is_superuser": False,
    }

    create_response = client.post("/api/v1/users/", json=user_payload, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()

    response = client.get(f"/api/v1/users/{created_user['id']}", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == created_user["id"]
    assert data["email"] == user_payload["email"]
    _assert_has_member_role(data)


def test_get_user_not_found(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/api/v1/users/999", headers=auth_headers)
    assert response.status_code == 404


def test_create_user(client: TestClient, auth_headers: dict) -> None:
    """Admins can create users and defaults include the member role."""

    user_payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }

    response = client.post("/api/v1/users/", json=user_payload, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == user_payload["email"]
    _assert_has_member_role(data)


def test_create_user_password_validation(client: TestClient, auth_headers: dict) -> None:
    weak_payload = {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "weak",
        "confirm_password": "weak",
        "is_active": True,
        "is_superuser": False,
    }
    response = client.post("/api/v1/users/", json=weak_payload, headers=auth_headers)
    assert response.status_code == 422

    mismatch_payload = {
        "email": "mismatch@example.com",
        "username": "mismatchuser",
        "password": "TestPass123!",
        "confirm_password": "DifferentPass123!",
        "is_active": True,
        "is_superuser": False,
    }
    response = client.post("/api/v1/users/", json=mismatch_payload, headers=auth_headers)
    assert response.status_code == 422


def test_update_user(client: TestClient, auth_headers: dict) -> None:
    user_payload = {
        "email": "updatetest@example.com",
        "username": "updateuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Update Test User",
        "is_active": True,
        "is_superuser": False,
    }
    create_response = client.post("/api/v1/users/", json=user_payload, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()

    update_payload = {
        "email": "updated@example.com",
        "username": "updateduser",
        "full_name": "Updated User",
    }
    response = client.put(
        f"/api/v1/users/{created_user['id']}",
        json=update_payload,
        headers=auth_headers,
    )
    assert response.status_code == 200
    _assert_has_member_role(response.json())


def test_delete_user(client: TestClient, auth_headers: dict) -> None:
    user_payload = {
        "email": "deletetest@example.com",
        "username": "deleteuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Delete Test User",
        "is_active": True,
        "is_superuser": False,
    }
    create_response = client.post("/api/v1/users/", json=user_payload, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()

    response = client.delete(f"/api/v1/users/{created_user['id']}", headers=auth_headers)
    assert response.status_code == 204


def test_search_users(client: TestClient, auth_headers: dict) -> None:
    user_payload = {
        "email": "searchtest@example.com",
        "username": "searchuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Search Test User",
        "is_active": True,
        "is_superuser": False,
    }
    assert client.post("/api/v1/users/", json=user_payload, headers=auth_headers).status_code == 201

    response = client.get("/api/v1/users/search/?query=searchuser", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert any(user["username"] == "searchuser" for user in data["items"])
    assert all("roles" in user for user in data["items"])


def test_get_active_users(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/api/v1/users/active/", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    for user in data["items"]:
        assert user["is_active"] is True
        assert "roles" in user


def test_member_cannot_list_users(client: TestClient, member_auth_headers: dict) -> None:
    response = client.get("/api/v1/users/", headers=member_auth_headers)
    assert response.status_code == 403


def test_member_cannot_create_users(client: TestClient, member_auth_headers: dict) -> None:
    user_payload = {
        "email": "unauthorized@example.com",
        "username": "unauthorized",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Unauthorized User",
        "is_active": True,
        "is_superuser": False,
    }
    response = client.post("/api/v1/users/", json=user_payload, headers=member_auth_headers)
    assert response.status_code == 403
