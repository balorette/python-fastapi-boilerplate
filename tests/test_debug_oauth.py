"""Debug test for OAuth login endpoint."""

import pytest
from unittest.mock import patch
from app.core.security import get_password_hash
from app.models.user import User


def test_debug_oauth_login(client):
    """Debug OAuth login to see what's failing."""
    
    # Create test user data
    test_user_data = {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "hashed_password": get_password_hash("TestPass123!")
    }
    
    # Mock the UserRepository methods
    with patch('app.repositories.user.UserRepository.get_by_email') as mock_get_by_email, \
         patch('app.repositories.user.UserRepository.update') as mock_update:
        
        # Create User object from test data
        user_obj = User(
            id=test_user_data["id"],
            email=test_user_data["email"],
            username=test_user_data.get("username", "testuser"),
            full_name=test_user_data["full_name"],
            hashed_password=test_user_data["hashed_password"],
            is_active=test_user_data["is_active"]
        )
        
        mock_get_by_email.return_value = user_obj
        mock_update.return_value = user_obj  # Return updated user

        # Test login endpoint
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123!",
                "grant_type": "password"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Headers: {response.headers}")
        
        # This will fail but we can see the debug info
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"Error JSON: {error_data}")
            except:
                print("Could not parse error as JSON")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"