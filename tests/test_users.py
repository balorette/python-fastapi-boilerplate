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
    response = client.get("/api/v1/users/1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "email" in data
    assert "username" in data


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
    update_data = {
        "email": "updated@example.com",
        "username": "updateduser"
    }
    response = client.put("/api/v1/users/1", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == update_data["email"]
    assert data["username"] == update_data["username"]


def test_delete_user(client: TestClient, auth_headers: dict):
    """Test deleting a user."""
    response = client.delete("/api/v1/users/1", headers=auth_headers)
    assert response.status_code == 204