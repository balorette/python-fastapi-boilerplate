"""Comprehensive tests for service layer patterns."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Optional

from app.services.user import UserService
from app.repositories.user import UserRepository
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserPasswordUpdate, UserResponse
from app.schemas.pagination import PaginatedResponse
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, AuthenticationError
from app.core.security import get_password_hash, verify_password


class TestUserService:
    """Test UserService functionality."""
    
    @pytest.fixture
    def mock_user_repo(self):
        """Create mock UserRepository."""
        repo = AsyncMock(spec=UserRepository)
        return repo
    
    @pytest.fixture
    def user_service(self, mock_user_repo):
        """Create UserService instance."""
        return UserService(mock_user_repo)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        return User(
            id=1,
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_users_list(self):
        """Create list of sample users."""
        return [
            User(id=1, username="user1", email="user1@example.com", full_name="User One", is_active=True),
            User(id=2, username="user2", email="user2@example.com", full_name="User Two", is_active=True),
            User(id=3, username="user3", email="user3@example.com", full_name="User Three", is_active=False)
        ]
    
    @pytest.mark.asyncio
    async def test_get_users_paginated_success(self, user_service, mock_user_repo, sample_users_list):
        """Test successful paginated user retrieval."""
        # Setup
        mock_user_repo.get_multi.return_value = sample_users_list
        mock_user_repo.count_records.return_value = 3
        
        # Execute
        result = await user_service.get_users_paginated(skip=0, limit=10)
        
        # Assert
        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 3
        assert result.total == 3
        assert result.page == 1
        assert result.total_pages == 1
        mock_user_repo.get_multi.assert_called_once_with(skip=0, limit=10)
        mock_user_repo.count_records.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_users_paginated_with_filters(self, user_service, mock_user_repo, sample_users_list):
        """Test paginated users with filtering."""
        # Setup
        active_users = [u for u in sample_users_list if u.is_active]
        mock_user_repo.get_multi.return_value = active_users
        mock_user_repo.count_records.return_value = 2
        
        # Execute
        result = await user_service.get_users_paginated(skip=0, limit=10, filters={"is_active": True})
        
        # Assert
        assert len(result.items) == 2
        assert result.total == 2
        mock_user_repo.get_multi.assert_called_once_with(skip=0, limit=10, filters={"is_active": True})
    
    @pytest.mark.asyncio
    async def test_search_users_success(self, user_service, mock_user_repo, sample_users_list):
        """Test user search functionality."""
        # Setup
        mock_user_repo.search_users.return_value = sample_users_list[:2]
        
        # Execute
        result = await user_service.search_users("user", skip=0, limit=10, active_only=False)
        
        # Assert
        assert len(result) == 2
        mock_user_repo.search_users.assert_called_once_with("user", skip=0, limit=10)
    
    @pytest.mark.asyncio
    async def test_search_users_active_only(self, user_service, mock_user_repo, sample_users_list):
        """Test user search with active_only filter."""
        # Setup
        active_users = [u for u in sample_users_list if u.is_active]
        mock_user_repo.get_active_users.return_value = active_users
        
        # Execute
        result = await user_service.search_users("user", skip=0, limit=10, active_only=True)
        
        # Assert
        assert len(result) == 2
        mock_user_repo.get_active_users.assert_called_once_with(skip=0, limit=10)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user retrieval by ID."""
        # Setup
        mock_user_repo.get.return_value = sample_user
        
        # Execute
        result = await user_service.get_user_by_id(1)
        
        # Assert
        assert result == sample_user
        mock_user_repo.get.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_user_repo):
        """Test user retrieval when user not found."""
        # Setup
        mock_user_repo.get.return_value = None
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User not found"):
            await user_service.get_user_by_id(999)
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user retrieval by email."""
        # Setup
        mock_user_repo.get_by_email.return_value = sample_user
        
        # Execute
        result = await user_service.get_user_by_email("test@example.com")
        
        # Assert
        assert result == sample_user
        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_service, mock_user_repo):
        """Test user retrieval by email when not found."""
        # Setup
        mock_user_repo.get_by_email.return_value = None
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User not found"):
            await user_service.get_user_by_email("nonexistent@example.com")
    
    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user retrieval by username."""
        # Setup
        mock_user_repo.get_by_username.return_value = sample_user
        
        # Execute
        result = await user_service.get_user_by_username("testuser")
        
        # Assert
        assert result == sample_user
        mock_user_repo.get_by_username.assert_called_once_with("testuser")
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user creation."""
        # Setup
        user_data = UserCreate(
            username="newuser",
            email="new@example.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
            full_name="New User",
            is_active=True,
            is_superuser=False
        )
        mock_user_repo.email_exists.return_value = False
        mock_user_repo.username_exists.return_value = False
        mock_user_repo.create.return_value = sample_user
        
        # Execute
        with patch('app.core.security.get_password_hash', return_value="hashed_password"):
            result = await user_service.create_user(user_data)
        
        # Assert
        assert result == sample_user
        mock_user_repo.email_exists.assert_called_once_with("new@example.com")
        mock_user_repo.username_exists.assert_called_once_with("newuser")
        mock_user_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, mock_user_repo):
        """Test user creation when email already exists."""
        # Setup
        user_data = UserCreate(
            username="newuser",
            email="existing@example.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
            full_name="New User",
            is_active=True,
            is_superuser=False
        )
        mock_user_repo.email_exists.return_value = True
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Email already registered"):
            await user_service.create_user(user_data)
    
    @pytest.mark.asyncio
    async def test_create_user_username_exists(self, user_service, mock_user_repo):
        """Test user creation when username already exists."""
        # Setup
        user_data = UserCreate(
            username="existinguser",
            email="new@example.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
            full_name="New User",
            is_active=True,
            is_superuser=False
        )
        mock_user_repo.email_exists.return_value = False
        mock_user_repo.username_exists.return_value = True
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Username already taken"):
            await user_service.create_user(user_data)
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user update."""
        # Setup
        update_data = UserUpdate(
            username="updateduser",
            email="updated@example.com",
            full_name="Updated User"
        )
        mock_user_repo.get.return_value = sample_user
        mock_user_repo.email_exists.return_value = False
        mock_user_repo.username_exists.return_value = False
        updated_user = User(**{**sample_user.__dict__, **update_data.model_dump(exclude_unset=True)})
        mock_user_repo.update.return_value = updated_user
        
        # Execute
        result = await user_service.update_user(1, update_data)
        
        # Assert
        assert result.username == "updateduser"
        mock_user_repo.get.assert_called_once_with(1)
        mock_user_repo.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service, mock_user_repo):
        """Test user update when user not found."""
        # Setup
        update_data = UserUpdate(username="updateduser", full_name="Updated User")
        mock_user_repo.get.return_value = None
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User not found"):
            await user_service.update_user(999, update_data)
    
    @pytest.mark.asyncio
    async def test_update_user_email_conflict(self, user_service, mock_user_repo, sample_user):
        """Test user update with email conflict."""
        # Setup
        update_data = UserUpdate(username="test", email="existing@example.com", full_name="Test User")
        mock_user_repo.get.return_value = sample_user
        mock_user_repo.email_exists.return_value = True
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Email already in use by another user"):
            await user_service.update_user(1, update_data)
    
    @pytest.mark.asyncio
    async def test_update_user_username_conflict(self, user_service, mock_user_repo, sample_user):
        """Test user update with username conflict."""
        # Setup
        update_data = UserUpdate(username="existinguser", full_name="Test User")
        mock_user_repo.get.return_value = sample_user
        mock_user_repo.email_exists.return_value = False
        mock_user_repo.username_exists.return_value = True
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Username already taken by another user"):
            await user_service.update_user(1, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user deletion."""
        # Setup
        mock_user_repo.get.return_value = sample_user
        mock_user_repo.delete.return_value = True
        
        # Execute
        result = await user_service.delete_user(1)
        
        # Assert
        assert result is True
        mock_user_repo.get.assert_called_once_with(1)
        mock_user_repo.delete.assert_called_once_with(sample_user)
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service, mock_user_repo):
        """Test user deletion when user not found."""
        # Setup
        mock_user_repo.get.return_value = None
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User not found"):
            await user_service.delete_user(999)
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user authentication."""
        # Setup
        sample_user.hashed_password = get_password_hash("testpass123")
        mock_user_repo.get_by_username.return_value = sample_user
        
        # Execute
        with patch('app.core.security.verify_password', return_value=True):
            result = await user_service.authenticate_user("testuser", "testpass123")
        
        # Assert
        assert result == sample_user
        mock_user_repo.get_by_username.assert_called_once_with("testuser")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_username(self, user_service, mock_user_repo):
        """Test authentication with invalid username."""
        # Setup
        mock_user_repo.get_by_username.return_value = None
        
        # Execute & Assert
        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            await user_service.authenticate_user("nonexistent", "password")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, user_service, mock_user_repo, sample_user):
        """Test authentication with invalid password."""
        # Setup
        sample_user.hashed_password = get_password_hash("correctpass")
        mock_user_repo.get_by_username.return_value = sample_user
        
        # Execute & Assert
        with patch('app.core.security.verify_password', return_value=False):
            with pytest.raises(AuthenticationError, match="Invalid username or password"):
                await user_service.authenticate_user("testuser", "wrongpass")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, user_service, mock_user_repo, sample_user):
        """Test authentication with inactive user."""
        # Setup
        sample_user.is_active = False
        sample_user.hashed_password = get_password_hash("testpass123")
        mock_user_repo.get_by_username.return_value = sample_user
        
        # Execute & Assert
        with patch('app.core.security.verify_password', return_value=True):
            with pytest.raises(AuthenticationError, match="User account is disabled"):
                await user_service.authenticate_user("testuser", "testpass123")
    
    @pytest.mark.asyncio
    async def test_update_password_success(self, user_service, mock_user_repo, sample_user):
        """Test successful password update."""
        # Setup
        password_data = UserPasswordUpdate(
            current_password="oldpass123",
            new_password="NewPass123!",
            confirm_new_password="NewPass123!"
        )
        sample_user.hashed_password = get_password_hash("oldpass123")
        mock_user_repo.get.return_value = sample_user
        mock_user_repo.update.return_value = sample_user
        
        # Execute
        with patch('app.core.security.verify_password', return_value=True):
            with patch('app.core.security.get_password_hash', return_value="new_hashed_password"):
                result = await user_service.update_password(1, password_data)
        
        # Assert
        assert result == sample_user
        mock_user_repo.get.assert_called_once_with(1)
        mock_user_repo.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_password_user_not_found(self, user_service, mock_user_repo):
        """Test password update when user not found."""
        # Setup
        password_data = UserPasswordUpdate(
            current_password="oldpass123",
            new_password="NewPass123!",
            confirm_new_password="NewPass123!"
        )
        mock_user_repo.get.return_value = None
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User not found"):
            await user_service.update_password(999, password_data)
    
    @pytest.mark.asyncio
    async def test_update_password_invalid_current(self, user_service, mock_user_repo, sample_user):
        """Test password update with invalid current password."""
        # Setup
        password_data = UserPasswordUpdate(
            current_password="wrongpass",
            new_password="NewPass123!",
            confirm_new_password="NewPass123!"
        )
        sample_user.hashed_password = get_password_hash("correctpass")
        mock_user_repo.get.return_value = sample_user
        
        # Execute & Assert
        with patch('app.core.security.verify_password', return_value=False):
            with pytest.raises(ValidationError, match="Current password is incorrect"):
                await user_service.update_password(1, password_data)
    
    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, user_service, mock_user_repo):
        """Test user statistics retrieval."""
        # Setup
        mock_user_repo.count_records.return_value = 10
        mock_user_repo.count_active_users.return_value = 8
        
        # Execute
        result = await user_service.get_user_stats()
        
        # Assert
        assert result.total_users == 10
        assert result.active_users == 8
        assert result.inactive_users == 2
        mock_user_repo.count_records.assert_called_once()
        mock_user_repo.count_active_users.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_users_by_date_range_success(self, user_service, mock_user_repo, sample_users_list):
        """Test user retrieval by date range."""
        # Setup
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        mock_user_repo.get_users_by_creation_date.return_value = sample_users_list
        
        # Execute
        result = await user_service.get_users_by_date_range(start_date, end_date)
        
        # Assert
        assert len(result) == 3
        mock_user_repo.get_users_by_creation_date.assert_called_once_with(start_date, end_date)