"""Comprehensive tests for service layer patterns."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List, Optional
from sqlalchemy import Result

from app.services.user import UserService
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserPasswordUpdate, UserResponse
from app.schemas.pagination import PaginatedResponse, PaginationParams, SearchParams, DateRangeParams
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, AuthenticationError


class TestUserService:
    """Test UserService functionality with proper session mocking."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session with proper execute method."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def user_service(self, mock_session):
        """Create UserService instance with mocked session."""
        return UserService(mock_session)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user with all required fields."""
        return User(
            id=1,
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
            hashed_password="$2b$12$test_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_users_list(self):
        """Create list of sample users with all required fields."""
        now = datetime.now()
        return [
            User(
                id=1, username="user1", email="user1@example.com", 
                full_name="User One", is_active=True, is_superuser=False,
                hashed_password="hash1", created_at=now, updated_at=now
            ),
            User(
                id=2, username="user2", email="user2@example.com", 
                full_name="User Two", is_active=True, is_superuser=False,
                hashed_password="hash2", created_at=now, updated_at=now
            ),
            User(
                id=3, username="user3", email="user3@example.com", 
                full_name="User Three", is_active=False, is_superuser=False,
                hashed_password="hash3", created_at=now, updated_at=now
            )
        ]
    
    def create_mock_result(self, data=None, count=None, scalar_return=None):
        """Create mock SQLAlchemy result."""
        result = Mock(spec=Result)
        
        # For scalar_one_or_none() methods (single record queries)
        if scalar_return is not None:
            result.scalar_one_or_none.return_value = scalar_return
        elif data is not None and not isinstance(data, list):
            result.scalar_one_or_none.return_value = data
        else:
            result.scalar_one_or_none.return_value = None
            
        # For scalar() methods (count queries)
        if count is not None:
            result.scalar.return_value = count
            
        # For scalars().all() methods (list queries)
        if data is not None:
            if isinstance(data, list):
                result.scalars.return_value.all.return_value = data
            else:
                result.scalars.return_value.all.return_value = [data]
        else:
            result.scalars.return_value.all.return_value = []
            
        return result
    
    # Test get_users_paginated method
    @pytest.mark.asyncio
    async def test_get_users_paginated_success(self, user_service, mock_session, sample_users_list):
        """Test successful paginated user retrieval."""
        # Setup
        params = PaginationParams(skip=0, limit=10, order_by=None)
        
        # Mock count query
        count_result = self.create_mock_result(count=3)
        # Mock get query
        get_result = self.create_mock_result(sample_users_list)
        
        mock_session.execute.side_effect = [count_result, get_result]
        
        # Execute
        result = await user_service.get_users_paginated(params)
        
        # Assert
        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 3
        assert result.total == 3
        assert result.page == 1
        assert mock_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_users_paginated_with_filters(self, user_service, mock_session, sample_users_list):
        """Test paginated users with filtering."""
        # Setup
        params = PaginationParams(skip=0, limit=10, order_by=None)
        filters = {"is_active": True}
        active_users = [u for u in sample_users_list if u.is_active]
        
        # Mock count query
        count_result = self.create_mock_result(count=2)
        # Mock get query 
        get_result = self.create_mock_result(active_users)
        
        mock_session.execute.side_effect = [count_result, get_result]
        
        # Execute
        result = await user_service.get_users_paginated(params, filters=filters)
        
        # Assert
        assert len(result.items) == 2
        assert result.total == 2
        assert mock_session.execute.call_count == 2
    
    # Test search_users method
    @pytest.mark.asyncio
    async def test_search_users_success(self, user_service, mock_session, sample_users_list):
        """Test user search functionality."""
        # Setup
        params = SearchParams(query="user", skip=0, limit=10, order_by=None)
        
        # Mock search queries (count then results)
        search_result = self.create_mock_result(sample_users_list[:2])
        count_result = self.create_mock_result(sample_users_list)
        
        mock_session.execute.side_effect = [count_result, search_result]
        
        # Execute
        result = await user_service.search_users(params)
        
        # Assert
        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 2
        assert result.total == 3
        assert mock_session.execute.call_count == 2
    
    # Test get_user method
    @pytest.mark.asyncio
    async def test_get_user_success(self, user_service, mock_session, sample_user):
        """Test successful user retrieval by ID."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        # Execute
        result = await user_service.get_user(1)
        
        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service, mock_session):
        """Test user retrieval when user not found."""
        # Setup
        get_result = self.create_mock_result(scalar_return=None)
        mock_session.execute.return_value = get_result
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User with ID 999 not found"):
            await user_service.get_user(999)
    
    # Test get_user_by_email method
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, user_service, mock_session, sample_user):
        """Test successful user retrieval by email."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        # Execute
        result = await user_service.get_user_by_email("test@example.com")
        
        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, user_service, mock_session):
        """Test user retrieval by email when not found."""
        # Setup
        get_result = self.create_mock_result(scalar_return=None)
        mock_session.execute.return_value = get_result
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User with email nonexistent@example.com not found"):
            await user_service.get_user_by_email("nonexistent@example.com")
    
    # Test get_user_by_username method
    @pytest.mark.asyncio
    async def test_get_user_by_username_success(self, user_service, mock_session, sample_user):
        """Test successful user retrieval by username."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        # Execute
        result = await user_service.get_user_by_username("testuser")
        
        # Assert
        assert result == sample_user
        mock_session.execute.assert_called_once()
    
    # Test create_user method
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_session, sample_user):
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
        
        # Mock email and username exist checks (return 0 count = doesn't exist)
        exist_result = self.create_mock_result(count=0)
        # Mock refresh result after creation
        refresh_result = self.create_mock_result(scalar_return=sample_user)
        
        mock_session.execute.side_effect = [exist_result, exist_result, refresh_result]
        mock_session.add = Mock()
        mock_session.refresh = AsyncMock()
        
        # Execute
        with patch.object(user_service, '_hash_password', return_value="hashed_password"):
            result = await user_service.create_user(user_data)
        
        # Assert
        assert result == sample_user
        assert mock_session.execute.call_count == 3  # 2 existence checks + 1 refresh query
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_email_exists(self, user_service, mock_session):
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
        
        # Mock email exists (return count > 0)
        exist_result = self.create_mock_result(count=1)
        mock_session.execute.return_value = exist_result
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Email existing@example.com is already registered"):
            await user_service.create_user(user_data)
    
    @pytest.mark.asyncio
    async def test_create_user_username_exists(self, user_service, mock_session):
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
        
        # Mock email doesn't exist but username exists
        email_result = self.create_mock_result(count=0)
        username_result = self.create_mock_result(count=1)
        mock_session.execute.side_effect = [email_result, username_result]
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Username existinguser is already taken"):
            await user_service.create_user(user_data)
    
    # Test update_user method
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_session, sample_user):
        """Test successful user update."""
        # Setup
        update_data = UserUpdate(
            username="updateduser",
            email="updated@example.com",
            full_name="Updated User"
        )
        
        # Mock get user
        get_result = self.create_mock_result(scalar_return=sample_user)
        # Mock email and username don't exist for other users (count=0)
        exist_result = self.create_mock_result(count=0)
        # Mock update result
        update_result = self.create_mock_result(scalar_return=sample_user)
        
        mock_session.execute.side_effect = [get_result, exist_result, exist_result, update_result]
        mock_session.refresh = AsyncMock()
        
        # Execute
        result = await user_service.update_user(1, update_data)
        
        # Assert
        assert result == sample_user
        assert mock_session.execute.call_count == 4
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_email_conflict(self, user_service, mock_session, sample_user):
        """Test user update with email conflict."""
        # Setup
        update_data = UserUpdate(username="gooduser", email="existing@example.com", full_name="Test User")
        
        # Mock get user
        get_result = self.create_mock_result(scalar_return=sample_user)
        # Mock email exists for another user (count=1)
        exist_result = self.create_mock_result(count=1)
        
        mock_session.execute.side_effect = [get_result, exist_result]
        
        # Execute & Assert
        with pytest.raises(ConflictError, match="Email existing@example.com is already in use"):
            await user_service.update_user(1, update_data)
    
    # Test delete_user method
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_session, sample_user):
        """Test successful user deletion."""
        # Setup
        # Mock record exists (count=1)
        exist_result = self.create_mock_result(count=1)
        # Mock get for delete
        get_result = self.create_mock_result(scalar_return=sample_user)
        
        mock_session.execute.side_effect = [exist_result, get_result]
        mock_session.delete = Mock()
        
        # Execute
        result = await user_service.delete_user(1)
        
        # Assert
        assert result is True
        assert mock_session.execute.call_count == 2
        mock_session.delete.assert_called_once_with(sample_user)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service, mock_session):
        """Test user deletion when user not found."""
        # Setup
        exist_result = self.create_mock_result(count=0)
        mock_session.execute.return_value = exist_result
        
        # Execute & Assert
        with pytest.raises(NotFoundError, match="User with ID 999 not found"):
            await user_service.delete_user(999)
    
    # Test authenticate_user method
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, user_service, mock_session, sample_user):
        """Test successful user authentication."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        with patch.object(user_service, '_verify_password', return_value=True):
            # Execute
            result = await user_service.authenticate_user("testuser", "testpass123")
            
            # Assert
            assert result == sample_user
            mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_username(self, user_service, mock_session):
        """Test authentication with invalid username."""
        # Setup - both username and email queries return None
        get_result = self.create_mock_result(scalar_return=None)
        mock_session.execute.return_value = get_result
        
        # Execute & Assert
        with pytest.raises(AuthenticationError, match="Invalid username/email or password"):
            await user_service.authenticate_user("nonexistent", "password")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, user_service, mock_session, sample_user):
        """Test authentication with invalid password."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        with patch.object(user_service, '_verify_password', return_value=False):
            # Execute & Assert
            with pytest.raises(AuthenticationError, match="Invalid username/email or password"):
                await user_service.authenticate_user("testuser", "wrongpass")
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(self, user_service, mock_session, sample_user):
        """Test authentication with inactive user."""
        # Setup
        sample_user.is_active = False
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        with patch.object(user_service, '_verify_password', return_value=True):
            # Execute & Assert
            with pytest.raises(AuthenticationError, match="User account is deactivated"):
                await user_service.authenticate_user("testuser", "testpass123")
    
    # Test update_password method
    @pytest.mark.asyncio
    async def test_update_password_success(self, user_service, mock_session, sample_user):
        """Test successful password update."""
        # Setup
        password_data = UserPasswordUpdate(
            current_password="oldpass123",
            new_password="NewPass123!",
            confirm_new_password="NewPass123!"
        )
        
        # Mock get user
        get_result = self.create_mock_result(scalar_return=sample_user)
        # Mock update result
        update_result = self.create_mock_result(scalar_return=sample_user)
        
        mock_session.execute.side_effect = [get_result, update_result]
        mock_session.refresh = AsyncMock()
        
        with patch.object(user_service, '_verify_password', return_value=True):
            with patch.object(user_service, '_hash_password', return_value="new_hashed_password"):
                # Execute
                result = await user_service.update_password(1, password_data)
                
                # Assert
                assert result == sample_user
                assert mock_session.execute.call_count == 2
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_password_invalid_current(self, user_service, mock_session, sample_user):
        """Test password update with invalid current password."""
        # Setup
        password_data = UserPasswordUpdate(
            current_password="wrongpass",
            new_password="NewPass123!",
            confirm_new_password="NewPass123!"
        )
        
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result
        
        with patch.object(user_service, '_verify_password', return_value=False):
            # Execute & Assert
            with pytest.raises(AuthenticationError, match="Current password is incorrect"):
                await user_service.update_password(1, password_data)
    
    # Test get_user_stats method
    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, user_service, mock_session):
        """Test user statistics retrieval."""
        # Setup - mock multiple count queries
        total_result = self.create_mock_result(count=10)
        active_result = self.create_mock_result(count=8)
        superuser_result = self.create_mock_result(count=2)
        recent_result = self.create_mock_result(count=1)
        
        mock_session.execute.side_effect = [total_result, active_result, superuser_result, recent_result]
        
        # Execute
        result = await user_service.get_user_stats()
        
        # Assert
        assert result['total_users'] == 10
        assert result['active_users'] == 8
        assert result['inactive_users'] == 2
        assert result['superusers'] == 2
        assert result['recent_registrations'] == 1
        assert mock_session.execute.call_count == 4
    
    # Test get_users_by_date_range method
    @pytest.mark.asyncio
    async def test_get_users_by_date_range_success(self, user_service, mock_session, sample_users_list):
        """Test user retrieval by date range."""
        # Setup
        date_params = DateRangeParams(
            start_date="2023-01-01T00:00:00",
            end_date="2023-12-31T23:59:59"
        )
        pagination_params = PaginationParams(skip=0, limit=10, order_by=None)
        
        # Mock count and get queries
        count_result = self.create_mock_result(count=3)
        get_result = self.create_mock_result(sample_users_list)
        
        mock_session.execute.side_effect = [count_result, get_result]
        
        # Execute
        result = await user_service.get_users_by_date_range(date_params, pagination_params)
        
        # Assert
        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 3
        assert result.total == 3
        assert mock_session.execute.call_count == 2