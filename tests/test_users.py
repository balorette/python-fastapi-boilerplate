"""Test user management endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_get_users(client: TestClient, auth_headers: dict):
    """Test getting list of users."""
    response = client.get("/api/v1/users/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_user_by_id(client: TestClient, auth_headers: dict):
    """Test getting user by ID."""
    # First create a user
    user_data = {
        "email": "gettest@example.com",
        "username": "getuser",
        "password": "testpassword123",
        "is_active": True
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


def test_get_user_not_found(client: TestClient, auth_headers: dict):
    """Test getting non-existent user."""
    response = client.get("/api/v1/users/999", headers=auth_headers)
    assert response.status_code == 404


def test_create_user(client: TestClient, auth_headers: dict):
    """Test creating a new user."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "is_active": True
    }
    response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]


def test_update_user(client: TestClient, auth_headers: dict):
    """Test updating a user."""
    # First create a user
    user_data = {
        "email": "updatetest@example.com",
        "username": "updateuser",
        "password": "testpassword123",
        "is_active": True
    }
    create_response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()
    
    # Now update the user
    update_data = {
        "email": "updated@example.com",
        "username": "updateduser"
    }
    response = client.put(f"/api/v1/users/{created_user['id']}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == update_data["email"]
    assert data["username"] == update_data["username"]


def test_delete_user(client: TestClient, auth_headers: dict):
    """Test deleting a user."""
    # First create a user
    user_data = {
        "email": "deletetest@example.com",
        "username": "deleteuser",
        "password": "testpassword123",
        "is_active": True
    }
    create_response = client.post("/api/v1/users/", json=user_data, headers=auth_headers)
    assert create_response.status_code == 201
    created_user = create_response.json()
    
    # Now delete the user
    response = client.delete(f"/api/v1/users/{created_user['id']}", headers=auth_headers)
    assert response.status_code == 204