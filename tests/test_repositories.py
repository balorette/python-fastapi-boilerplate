"""Comprehensive tests for repository patterns."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository
from app.repositories.user import UserRepository
from app.models.user import User
from app.core.exceptions import NotFoundError, ConflictError


class TestBaseRepository:
    """Test BaseRepository functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session for testing."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.get = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def base_repo(self, mock_session):
        """Create BaseRepository instance."""
        return BaseRepository(User, mock_session)
    
    @pytest.mark.asyncio
    async def test_get_with_relationships(self, base_repo, mock_session):
        """Test get method with relationship loading."""
        # Setup
        mock_user = User(id=1, username="testuser", email="test@example.com")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await base_repo.get(1, load_relationships=True)
        
        # Assert
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_not_found(self, base_repo, mock_session):
        """Test get method when record not found."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await base_repo.get(1)
        
        # Assert - BaseRepository get() returns None, doesn't raise
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_multi_with_filters(self, base_repo, mock_session):
        """Test get_multi with advanced filtering."""
        # Setup
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            User(id=1, username="user1", email="user1@example.com"),
            User(id=2, username="user2", email="user2@example.com")
        ]
        mock_session.execute.return_value = mock_result
        
        # Execute
        filters = {"is_active": True}
        result = await base_repo.get_multi(filters=filters, skip=0, limit=10)
        
        # Assert
        assert len(result) == 2
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_multi_with_ordering(self, base_repo, mock_session):
        """Test get_multi with ordering."""
        # Setup
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # Execute
        await base_repo.get_multi(order_by="created_at")
        
        # Assert
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_records(self, base_repo, mock_session):
        """Test count_records method."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        # Execute
        count = await base_repo.count_records()
        
        # Assert
        assert count == 5
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_exists(self, base_repo, mock_session):
        """Test record_exists method."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        # Execute
        exists = await base_repo.record_exists(1)
        
        # Assert
        assert exists is True
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_success(self, base_repo, mock_session):
        """Test successful record creation."""
        # Setup
        user_data = {"username": "newuser", "email": "new@example.com"}
        
        # Execute
        result = await base_repo.create(user_data)
        
        # Assert
        assert isinstance(result, User)
        assert result.username == "newuser"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_conflict(self, base_repo, mock_session):
        """Test creation with database conflict."""
        # Setup
        user_data = {"username": "existinguser", "email": "existing@example.com"}
        from sqlalchemy.exc import IntegrityError
        mock_session.commit.side_effect = IntegrityError("test", "test", Exception("test"))
        
        # Execute & Assert
        with pytest.raises(IntegrityError):
            await base_repo.create(user_data)
        
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_success(self, base_repo, mock_session):
        """Test successful record update."""
        # Setup
        mock_user = User(id=1, username="olduser", email="old@example.com")
        update_data = {"username": "newuser"}
        
        # Execute
        result = await base_repo.update(mock_user, update_data)
        
        # Assert
        assert result.username == "newuser"
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


class TestUserRepository:
    """Test UserRepository specific functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock session for testing."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.get = AsyncMock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        return session
    
    @pytest.fixture
    def user_repo(self, mock_session):
        """Create UserRepository instance."""
        return UserRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repo, mock_session):
        """Test get_by_email method."""
        # Setup
        mock_user = User(id=1, username="testuser", email="test@example.com")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await user_repo.get_by_email("test@example.com")
        
        # Assert
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_username(self, user_repo, mock_session):
        """Test get_by_username method."""
        # Setup
        mock_user = User(id=1, username="testuser", email="test@example.com")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await user_repo.get_by_username("testuser")
        
        # Assert
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_users(self, user_repo, mock_session):
        """Test search_users method."""
        # Setup
        mock_users = [
            User(id=1, username="john", email="john@example.com", full_name="John Doe"),
            User(id=2, username="jane", email="jane@example.com", full_name="Jane Smith")
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await user_repo.search_users("john", skip=0, limit=10)
        
        # Assert
        assert len(result) == 2
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_users(self, user_repo, mock_session):
        """Test get_active_users method."""
        # Setup
        mock_users = [
            User(id=1, username="user1", email="user1@example.com", is_active=True),
            User(id=2, username="user2", email="user2@example.com", is_active=True)
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await user_repo.get_active_users(skip=0, limit=10)
        
        # Assert
        assert len(result) == 2
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_exists(self, user_repo, mock_session):
        """Test email_exists method."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = 1  # ID found
        mock_session.execute.return_value = mock_result
        
        # Execute
        exists = await user_repo.email_exists("test@example.com")
        
        # Assert
        assert exists is True
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_exists_with_exclude(self, user_repo, mock_session):
        """Test email_exists method with user exclusion."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # No records found when excluding the user
        mock_session.execute.return_value = mock_result
        
        # Execute
        exists = await user_repo.email_exists("test@example.com", exclude_id=1)
        
        # Assert
        assert exists is False
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_username_exists(self, user_repo, mock_session):
        """Test username_exists method."""
        # Setup
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = 1  # ID found
        mock_session.execute.return_value = mock_result
        
        # Execute
        exists = await user_repo.username_exists("testuser")
        
        # Assert
        assert exists is True
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_active_users(self, user_repo, mock_session):
        """Test count_active_users method."""
        # Setup
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        # Execute
        count = await user_repo.count_active_users()
        
        # Assert
        assert count == 5
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_users_by_creation_date(self, user_repo, mock_session):
        """Test get_users_by_creation_date method."""
        # Setup
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        mock_users = [
            User(id=1, username="user1", email="user1@example.com", created_at=start_date + timedelta(days=1)),
            User(id=2, username="user2", email="user2@example.com", created_at=start_date + timedelta(days=2))
        ]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute.return_value = mock_result
        
        # Execute
        result = await user_repo.get_users_by_creation_date(start_date, end_date)
        
        # Assert
        assert len(result) == 2
        mock_session.execute.assert_called_once()