"""Comprehensive tests for service layer patterns."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy import Result

from app.core.authz import DEFAULT_ROLE_PERMISSIONS, SystemRole
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.oauth import GoogleUserInfo, OAuthUserCreate
from app.schemas.pagination import (
    DateRangeParams,
    PaginatedResponse,
    PaginationParams,
    SearchParams,
)
from app.schemas.user import UserCreate, UserPasswordUpdate, UserUpdate


class TestUserService:
    """Test UserService functionality with proper session mocking."""

    @pytest.fixture
    def user_service(self, user_service_factory, mock_session):
        """Create UserService instance with mocked session."""
        service = user_service_factory(mock_session)

        async def _get_roles_by_names(names: list[str]) -> list[Role]:
            roles: list[Role] = []
            for role_name in names:
                role = Role(name=role_name, description=f"Mock role {role_name}")
                try:
                    role_enum = SystemRole(role_name)
                except ValueError:
                    permission_values: tuple[str, ...] = ()
                else:
                    permission_values = tuple(
                        permission.value
                        for permission in DEFAULT_ROLE_PERMISSIONS.get(role_enum, ())
                    )
                role.permissions = [
                    Permission(name=value, description=value)
                    for value in permission_values
                ]
                roles.append(role)
            return roles

        service.role_repository.get_by_names = AsyncMock(
            side_effect=_get_roles_by_names
        )
        return service

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
            updated_at=datetime.now(),
        )

    @pytest.fixture
    def sample_users_list(self):
        """Create list of sample users with all required fields."""
        now = datetime.now()
        return [
            User(
                id=1,
                username="user1",
                email="user1@example.com",
                full_name="User One",
                is_active=True,
                is_superuser=False,
                hashed_password="hash1",
                created_at=now,
                updated_at=now,
            ),
            User(
                id=2,
                username="user2",
                email="user2@example.com",
                full_name="User Two",
                is_active=True,
                is_superuser=False,
                hashed_password="hash2",
                created_at=now,
                updated_at=now,
            ),
            User(
                id=3,
                username="user3",
                email="user3@example.com",
                full_name="User Three",
                is_active=False,
                is_superuser=False,
                hashed_password="hash3",
                created_at=now,
                updated_at=now,
            ),
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
    async def test_get_users_paginated_success(
        self, user_service, mock_session, sample_users_list
    ):
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
    async def test_update_user_success(self, user_service, sample_user):
        """Ensure update_user delegates to repository after validation."""
        updated_user = deepcopy(sample_user)
        updated_user.email = "new@example.com"

        user_service.get_user = AsyncMock(return_value=sample_user)
        user_service.repository.exists = AsyncMock(side_effect=[False, False])
        user_service.repository.update = AsyncMock(return_value=updated_user)

        result = await user_service.update_user(
            sample_user.id, UserUpdate(email="new@example.com")
        )

        assert result.email == "new@example.com"
        user_service.repository.update.assert_awaited_once()
        assert user_service.repository.exists.await_count == 2

    @pytest.mark.asyncio
    async def test_update_user_conflict_email(self, user_service, sample_user):
        """Conflict is raised when updating to a duplicate email."""
        user_service.get_user = AsyncMock(return_value=sample_user)
        user_service.repository.exists = AsyncMock(return_value=True)

        with pytest.raises(ConflictError):
            await user_service.update_user(
                sample_user.id, UserUpdate(email="dup@example.com")
            )

    @pytest.mark.asyncio
    async def test_get_active_users_paginated(
        self, user_service, sample_users_list, mock_session
    ):
        """Active user pagination proxies to repository counts."""
        params = PaginationParams(skip=0, limit=10, order_by=None)
        user_service.repository.count_records = AsyncMock(return_value=2)
        user_service.repository.get_multi = AsyncMock(
            return_value=sample_users_list[:2]
        )

        result = await user_service.get_active_users_paginated(params)

        assert result.total == 2
        assert len(result.items) == 2
        user_service.repository.count_records.assert_awaited_with({"is_active": True})
        user_service.repository.get_multi.assert_awaited()

    @pytest.mark.asyncio
    async def test_get_users_by_date_range(self, user_service, sample_users_list):
        """Date range filtering composes repository filters."""
        date_params = DateRangeParams(start_date="2024-01-01", end_date="2024-01-31")
        pagination = PaginationParams(skip=0, limit=10, order_by=None)

        user_service.repository.count_records = AsyncMock(return_value=1)
        user_service.repository.get_users_by_creation_date = AsyncMock(
            return_value=sample_users_list[:1]
        )

        result = await user_service.get_users_by_date_range(date_params, pagination)

        assert result.total == 1
        user_service.repository.count_records.assert_awaited_with(
            {"created_at": {"gte": "2024-01-01", "lte": "2024-01-31"}}
        )

    @pytest.mark.asyncio
    async def test_ensure_unique_username_handles_collisions(self, user_service):
        """Username collisions receive numeric suffixes."""
        user_service.repository.exists = AsyncMock(side_effect=[True, True, False])

        result = await user_service._ensure_unique_username("tester")

        assert result == "tester2"
        assert user_service.repository.exists.await_count == 3

    @pytest.mark.asyncio
    async def test_update_password_success(self, user_service, sample_user):
        """Passwords can be rotated when verification passes."""
        user_service.get_user = AsyncMock(return_value=sample_user)
        user_service._verify_password = MagicMock(return_value=True)
        user_service._hash_password = MagicMock(return_value="new-hash")
        user_service.repository.update = AsyncMock(return_value=sample_user)

        result = await user_service.update_password(
            sample_user.id,
            UserPasswordUpdate(
                current_password="OldPass1!",
                new_password="NewPass1!",
                confirm_new_password="NewPass1!",
            ),
        )

        assert result == sample_user
        user_service.repository.update.assert_awaited_with(
            sample_user, {"hashed_password": "new-hash"}
        )

    @pytest.mark.asyncio
    async def test_update_password_invalid_current(self, user_service, sample_user):
        """Invalid current passwords raise authentication errors."""
        user_service.get_user = AsyncMock(return_value=sample_user)
        user_service._verify_password = MagicMock(return_value=False)

        with pytest.raises(AuthenticationError):
            await user_service.update_password(
                sample_user.id,
                UserPasswordUpdate(
                    current_password="BadPass1!",
                    new_password="NewPass1!",
                    confirm_new_password="NewPass1!",
                ),
            )

    @pytest.mark.asyncio
    async def test_update_password_oauth_only(self, user_service, sample_user):
        """OAuth-only accounts cannot rotate passwords."""
        oauth_only = deepcopy(sample_user)
        oauth_only.hashed_password = None

        user_service.get_user = AsyncMock(return_value=oauth_only)

        with pytest.raises(ValidationError):
            await user_service.update_password(
                oauth_only.id,
                UserPasswordUpdate(
                    current_password="Irrelev1!",
                    new_password="NewPass1!",
                    confirm_new_password="NewPass1!",
                ),
            )

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service):
        """Deleting a missing user raises NotFoundError."""
        user_service.repository.record_exists = AsyncMock(return_value=False)

        with pytest.raises(NotFoundError):
            await user_service.delete_user(999)

    @pytest.mark.asyncio
    async def test_activate_user(self, user_service, sample_user):
        """Activation toggles inactive accounts."""
        inactive = deepcopy(sample_user)
        inactive.is_active = False
        activated = deepcopy(sample_user)
        activated.is_active = True

        user_service.get_user = AsyncMock(return_value=inactive)
        user_service.repository.update = AsyncMock(return_value=activated)

        result = await user_service.activate_user(inactive.id)

        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, sample_user):
        """Deactivation toggles active accounts."""
        active = deepcopy(sample_user)
        deactivated = deepcopy(sample_user)
        deactivated.is_active = False

        user_service.get_user = AsyncMock(return_value=active)
        user_service.repository.update = AsyncMock(return_value=deactivated)

        result = await user_service.deactivate_user(active.id)

        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_create_or_update_oauth_user_updates_existing(
        self, user_service, sample_user
    ):
        """Existing OAuth users are updated rather than recreated."""
        user_service.get_by_oauth_id = AsyncMock(return_value=sample_user)
        user_service.repository.update = AsyncMock(return_value=sample_user)

        google_info = GoogleUserInfo(
            id="google-id",
            email=sample_user.email,
            verified_email=True,
            name="Test User",
            given_name="Test",
            family_name="User",
            picture=None,
            locale="en-US",
        )

        user, is_new = await user_service.create_or_update_oauth_user(
            google_info, refresh_token="refresh"
        )

        assert user == sample_user
        assert is_new is False
        user_service.repository.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_or_update_oauth_user_creates_new(
        self, user_service, mock_session
    ):
        """New OAuth identities create fresh accounts with unique usernames."""
        user_service.get_by_oauth_id = AsyncMock(return_value=None)
        user_service.repository.get_by_email = AsyncMock(return_value=None)
        user_service.repository.exists = AsyncMock(side_effect=[False, False])

        new_user = MagicMock()
        new_user.is_superuser = False
        user_service.repository.create = AsyncMock(return_value=new_user)

        google_info = GoogleUserInfo(
            id="new-id",
            email="new@example.com",
            verified_email=True,
            name="New User",
            given_name="New",
            family_name="User",
            picture=None,
            locale="en-US",
        )

        user, is_new = await user_service.create_or_update_oauth_user(
            google_info, refresh_token="refresh"
        )

        assert user == new_user
        assert is_new is True
        user_service.repository.create.assert_awaited_once()
        assert user_service.repository.exists.await_count >= 1

    @pytest.mark.asyncio
    async def test_create_oauth_user_links_existing(self, user_service, sample_user):
        """Existing email triggers account linking."""
        user_service.repository.get_by_email = AsyncMock(return_value=sample_user)
        user_service.link_oauth_account = AsyncMock(return_value=sample_user)

        oauth_payload = GoogleUserInfo(
            id="google-id",
            email=sample_user.email,
            verified_email=True,
            name="Test User",
            given_name="Test",
            family_name="User",
            picture=None,
            locale="en-US",
        )

        result = await user_service.create_oauth_user(
            OAuthUserCreate(
                email=oauth_payload.email,
                username=sample_user.username,
                full_name=oauth_payload.name,
                oauth_provider="google",
                oauth_id=oauth_payload.id,
                oauth_email_verified=True,
                oauth_refresh_token="refresh",
                is_active=True,
                is_superuser=False,
            )
        )

        assert result == sample_user
        user_service.link_oauth_account.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_link_oauth_account_success(self, user_service, sample_user):
        """Linking OAuth data updates the repository and commits."""
        user_service.get_user = AsyncMock(return_value=sample_user)
        user_service.repository.update = AsyncMock(return_value=sample_user)

        oauth_payload = OAuthUserCreate(
            email=sample_user.email,
            username=sample_user.username,
            full_name=sample_user.full_name,
            oauth_provider="google",
            oauth_id="google-id",
            oauth_email_verified=True,
            oauth_refresh_token="refresh",
            is_active=True,
            is_superuser=False,
        )

        result = await user_service.link_oauth_account(sample_user.id, oauth_payload)

        assert result == sample_user

    @pytest.mark.asyncio
    async def test_link_oauth_account_conflict(self, user_service, sample_user):
        """Conflicts rollback the session during linking."""
        user_service.get_user = AsyncMock(return_value=sample_user)
        user_service.repository.update = AsyncMock(side_effect=Exception("boom"))

        oauth_payload = OAuthUserCreate(
            email=sample_user.email,
            username=sample_user.username,
            full_name=sample_user.full_name,
            oauth_provider="google",
            oauth_id="google-id",
            oauth_email_verified=True,
            oauth_refresh_token="refresh",
            is_active=True,
            is_superuser=False,
        )

        with pytest.raises(ConflictError):
            await user_service.link_oauth_account(sample_user.id, oauth_payload)

    @pytest.mark.asyncio
    async def test_authenticate_oauth_user_success(self, user_service, sample_user):
        """OAuth authentication returns active users."""
        user_service.get_by_oauth_id = AsyncMock(return_value=sample_user)

        result = await user_service.authenticate_oauth_user("google", "id")

        assert result == sample_user

    @pytest.mark.asyncio
    async def test_authenticate_oauth_user_missing(self, user_service, sample_user):
        """Missing OAuth accounts raise authentication errors."""
        user_service.get_by_oauth_id = AsyncMock(return_value=None)

        with pytest.raises(AuthenticationError):
            await user_service.authenticate_oauth_user("google", "id")

    @pytest.mark.asyncio
    async def test_authenticate_oauth_user_inactive(self, user_service, sample_user):
        """Inactive OAuth accounts are rejected."""
        inactive_user = deepcopy(sample_user)
        inactive_user.is_active = False
        user_service.get_by_oauth_id = AsyncMock(return_value=inactive_user)

        with pytest.raises(AuthenticationError):
            await user_service.authenticate_oauth_user("google", "id")

    @pytest.mark.asyncio
    async def test_get_user_stats(self, user_service):
        """Aggregated user stats return computed fields."""
        user_service.repository.count_records = AsyncMock(side_effect=[10, 7, 2, 1])

        stats = await user_service.get_user_stats()

        assert stats["total_users"] == 10
        assert stats["active_users"] == 7
        assert stats["inactive_users"] == 3

    @pytest.mark.asyncio
    async def test_get_users_paginated_with_filters(
        self, user_service, mock_session, sample_users_list
    ):
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
    async def test_search_users_success(
        self, user_service, mock_session, sample_users_list
    ):
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
    async def test_get_user_by_email_success(
        self, user_service, mock_session, sample_user
    ):
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
        with pytest.raises(
            NotFoundError, match="User with email nonexistent@example.com not found"
        ):
            await user_service.get_user_by_email("nonexistent@example.com")

    # Test get_user_by_username method
    @pytest.mark.asyncio
    async def test_get_user_by_username_success(
        self, user_service, mock_session, sample_user
    ):
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
            is_superuser=False,
        )

        # Mock email and username exist checks (return None = doesn't exist)
        exist_result = self.create_mock_result(scalar_return=None)
        mock_session.execute.side_effect = [exist_result, exist_result]
        mock_session.add = Mock()
        mock_session.refresh = AsyncMock(
            return_value=None
        )  # refresh modifies object in place

        # Execute
        with patch.object(
            user_service, "_hash_password", return_value="hashed_password"
        ):
            result = await user_service.create_user(user_data)

        # Assert
        assert result is not None
        assert isinstance(result, User)
        assert result.email == user_data.email
        assert result.username == user_data.username
        assert result.full_name == user_data.full_name
        assert result.hashed_password == "hashed_password"
        assert mock_session.execute.call_count == 2  # 2 existence checks only
        mock_session.add.assert_called_once()
        # first commit persists user, second assigns roles
        assert mock_session.commit.call_count == 2

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
            is_superuser=False,
        )

        # Mock email exists (return something for scalar_one_or_none)
        exist_result = self.create_mock_result(
            scalar_return=1
        )  # Any non-None value means exists
        mock_session.execute.return_value = exist_result

        # Execute & Assert
        with pytest.raises(
            ConflictError, match="Email existing@example.com is already registered"
        ):
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
            is_superuser=False,
        )

        # Mock email doesn't exist (None) but username exists (non-None)
        email_result = self.create_mock_result(scalar_return=None)
        username_result = self.create_mock_result(scalar_return=1)
        mock_session.execute.side_effect = [email_result, username_result]

        # Execute & Assert
        with pytest.raises(
            ConflictError, match="Username existinguser is already taken"
        ):
            await user_service.create_user(user_data)

    @pytest.mark.asyncio
    async def test_update_user_email_conflict(
        self, user_service, mock_session, sample_user
    ):
        """Test user update with email conflict."""
        # Setup
        update_data = UserUpdate(
            username="gooduser", email="existing@example.com", full_name="Test User"
        )

        # Mock get user
        get_result = self.create_mock_result(scalar_return=sample_user)
        # Mock email exists for another user (scalar_one_or_none returns a user record)
        conflict_user = User(
            id=2,
            username="other",
            email="existing@example.com",
            full_name="Other User",
            is_active=True,
            is_superuser=False,
            hashed_password="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        exist_result = self.create_mock_result(scalar_return=conflict_user)

        mock_session.execute.side_effect = [get_result, exist_result]

        # Execute & Assert
        with pytest.raises(
            ConflictError, match="Email existing@example.com is already in use"
        ):
            await user_service.update_user(1, update_data)

    # Test authenticate_user method
    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, user_service, mock_session, sample_user
    ):
        """Test successful user authentication."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result

        with patch.object(user_service, "_verify_password", return_value=True):
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
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await user_service.authenticate_user("nonexistent", "password")

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(
        self, user_service, mock_session, sample_user
    ):
        """Test authentication with invalid password."""
        # Setup
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result

        with patch.object(
            user_service, "_verify_password", return_value=False
        ), pytest.raises(AuthenticationError, match="Invalid credentials"):
            await user_service.authenticate_user("testuser", "wrongpass")

    @pytest.mark.asyncio
    async def test_authenticate_user_inactive(
        self, user_service, mock_session, sample_user
    ):
        """Test authentication with inactive user."""
        # Setup
        sample_user.is_active = False
        get_result = self.create_mock_result(scalar_return=sample_user)
        mock_session.execute.return_value = get_result

        with patch.object(
            user_service, "_verify_password", return_value=True
        ), pytest.raises(AuthorizationError, match="Account is disabled"):
            await user_service.authenticate_user("testuser", "testpass123")

    # Test get_user_stats method
    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, user_service, mock_session):
        """Test user statistics retrieval."""
        # Setup - mock multiple count queries
        total_result = self.create_mock_result(count=10)
        active_result = self.create_mock_result(count=8)
        superuser_result = self.create_mock_result(count=2)
        recent_result = self.create_mock_result(count=1)

        mock_session.execute.side_effect = [
            total_result,
            active_result,
            superuser_result,
            recent_result,
        ]

        # Execute
        result = await user_service.get_user_stats()

        # Assert
        assert result["total_users"] == 10
        assert result["active_users"] == 8
        assert result["inactive_users"] == 2
        assert result["superusers"] == 2
        assert result["recent_registrations"] == 1
        assert mock_session.execute.call_count == 4

    # Test get_users_by_date_range method
    @pytest.mark.asyncio
    async def test_get_users_by_date_range_success(
        self, user_service, mock_session, sample_users_list
    ):
        """Test user retrieval by date range."""
        # Setup
        date_params = DateRangeParams(
            start_date="2023-01-01T00:00:00", end_date="2023-12-31T23:59:59"
        )
        pagination_params = PaginationParams(skip=0, limit=10, order_by=None)

        # Mock count and get queries
        count_result = self.create_mock_result(count=3)
        get_result = self.create_mock_result(sample_users_list)

        mock_session.execute.side_effect = [count_result, get_result]

        # Execute
        result = await user_service.get_users_by_date_range(
            date_params, pagination_params
        )

        # Assert
        assert isinstance(result, PaginatedResponse)
        assert len(result.items) == 3
        assert result.total == 3
        assert mock_session.execute.call_count == 2
