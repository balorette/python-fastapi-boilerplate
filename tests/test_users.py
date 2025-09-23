"""Test user management endpoints with enhanced schemas."""

import pytest
from fastapi.testclient import TestClient


def test_get_users(client: TestClient, auth_headers: dict):
    """Test getting paginated list of users."""
    response = client.get("/api/v1/users/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert isinstance(data["items"], list)


def test_get_user_by_id(client: TestClient, auth_headers: dict):
    """Test getting user by ID."""
    # First create a user
    user_data = {
        "email": "gettest@example.com",
        "username": "getuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Get Test User",
        "is_active": True,
        "is_superuser": False
    }
    create_response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()
    
    # Now get the user by ID
    response = client.get(f"/api/v1/users/{created_user['id']}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_user["id"]
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["full_name"] == user_data["full_name"]


def test_get_user_not_found(client: TestClient, auth_headers: dict):
    """Test getting non-existent user."""
    response = client.get("/api/v1/users/999", headers=auth_headers)
    assert response.status_code == 404


def test_create_user(client: TestClient, auth_headers: dict):
    """Test creating a new user with enhanced validation."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False
    }
    response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["full_name"] == user_data["full_name"]
    assert data["is_active"] == user_data["is_active"]
    assert data["is_superuser"] == user_data["is_superuser"]


def test_create_user_password_validation(client: TestClient, auth_headers: dict):
    """Test password validation during user creation."""
    # Test weak password
    user_data = {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "weak",
        "confirm_password": "weak",
        "is_active": True,
        "is_superuser": False
    }
    response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 422
    
    # Test password mismatch
    user_data = {
        "email": "mismatch@example.com",
        "username": "mismatchuser",
        "password": "TestPass123!",
        "confirm_password": "DifferentPass123!",
        "is_active": True,
        "is_superuser": False
    }
    response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 422


def test_update_user(client: TestClient, auth_headers: dict):
    """Test updating a user."""
    # First create a user
    user_data = {
        "email": "updatetest@example.com",
        "username": "updateuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Update Test User",
        "is_active": True,
        "is_superuser": False
    }
    create_response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()
    
    # Now update the user
    update_data = {
        "email": "updated@example.com",
        "username": "updateduser",
        "full_name": "Updated User"
    }
    response = client.put(f"/api/v1/users/{created_user['id']}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == update_data["email"]
    assert data["username"] == update_data["username"]
    assert data["full_name"] == update_data["full_name"]


def test_delete_user(client: TestClient, auth_headers: dict):
    """Test deleting a user."""
    # First create a user
    user_data = {
        "email": "deletetest@example.com",
        "username": "deleteuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Delete Test User",
        "is_active": True,
        "is_superuser": False
    }
    create_response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()
    
    # Now delete the user
    response = client.delete(f"/api/v1/users/{created_user['id']}", headers=auth_headers)
    assert response.status_code == 204


def test_search_users(client: TestClient, auth_headers: dict):
    """Test searching users."""
    # First create a user to search for
    user_data = {
        "email": "searchtest@example.com",
        "username": "searchuser",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "full_name": "Search Test User",
        "is_active": True,
        "is_superuser": False
    }
    create_response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 201
    
    # Search for the user
    response = client.get("/api/v1/users/search/?query=searchuser", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert any(user["username"] == "searchuser" for user in data["items"])


def test_get_active_users(client: TestClient, auth_headers: dict):
    """Test getting active users only."""
    response = client.get("/api/v1/users/active/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    # All returned users should be active
    for user in data["items"]:
        assert user["is_active"] is True