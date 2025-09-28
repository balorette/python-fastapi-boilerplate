"""Integration tests for UserService with real PostgreSQL database operations."""

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.services.user import UserService
from app.schemas.user import UserCreate, UserUpdate, UserPasswordUpdate
from app.schemas.pagination import PaginationParams, SearchParams, DateRangeParams
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, AuthenticationError


class TestUserServiceIntegration:
    """Test UserService with real database operations and constraints."""

    @pytest.mark.asyncio
    async def test_create_user_full_database_flow(self, async_db_session: AsyncSession):
        """Test complete user creation with real database operations."""
        service = UserService(async_db_session)
        
        user_data = UserCreate(
            email="integration@example.com",
            username="integrationuser", 
            password="TestPass123!",
            confirm_password="TestPass123!",
            full_name="Integration Test User"
        )
        
        # Create user
        created_user = await service.create_user(user_data)
        
        # Validate user was created correctly in database
        assert created_user.id is not None
        assert created_user.email == user_data.email
        assert created_user.username == user_data.username
        assert created_user.full_name == user_data.full_name
        assert created_user.is_active is True
        assert created_user.hashed_password is not None
        assert created_user.hashed_password != user_data.password  # Should be hashed
        assert created_user.created_at is not None
        assert created_user.updated_at is not None
        
        # Verify user exists in database by retrieving
        retrieved_user = await service.get_user(created_user.id)
        assert retrieved_user.email == user_data.email
        assert retrieved_user.username == user_data.username
        
        # Verify user can be found by email
        user_by_email = await service.get_user_by_email(user_data.email)
        assert user_by_email.id == created_user.id
        
        # Verify user can be found by username
        user_by_username = await service.get_user_by_username(user_data.username)
        assert user_by_username.id == created_user.id

    @pytest.mark.asyncio
    async def test_database_constraint_violations(self, async_db_session: AsyncSession, sample_user_in_db):
        """Test real database constraint violations."""
        service = UserService(async_db_session)
        
        # Test duplicate email constraint
        duplicate_email_data = UserCreate(
            email=sample_user_in_db.email,  # Duplicate email
            username="differentuser",
            password="TestPass123!",
            confirm_password="TestPass123!",
            full_name="Different User"
        )
        
        with pytest.raises(ConflictError, match="Email .* is already registered"):
            await service.create_user(duplicate_email_data)

        # Test duplicate username constraint  
        duplicate_username_data = UserCreate(
            email="different@example.com",
            username=sample_user_in_db.username,  # Duplicate username
            password="TestPass123!",
            confirm_password="TestPass123!",
            full_name="Different User"
        )
        
        with pytest.raises(ConflictError, match="Username .* is already taken"):
            await service.create_user(duplicate_username_data)
            
    @pytest.mark.asyncio
    async def test_real_password_authentication(self, async_db_session: AsyncSession, sample_user_in_db):
        """Test authentication with real password hashing and verification."""
        service = UserService(async_db_session)
        
        # Should succeed with correct password
        authenticated_user = await service.authenticate_user(sample_user_in_db.username, "TestPass123!")
        assert authenticated_user.id == sample_user_in_db.id
        assert authenticated_user.email == sample_user_in_db.email
        
        # Should fail with wrong password
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await service.authenticate_user(sample_user_in_db.username, "WrongPassword123!")

        # Should fail with non-existent user
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await service.authenticate_user("nonexistentuser", "TestPass123!")
            
        # Should work with email as username
        authenticated_user = await service.authenticate_user(sample_user_in_db.email, "TestPass123!")
        assert authenticated_user.id == sample_user_in_db.id

    @pytest.mark.asyncio
    async def test_user_update_with_database_constraints(self, async_db_session: AsyncSession):
        """Test user updates with real database constraint checking."""
        service = UserService(async_db_session)
        
        # Create two users
        user1_data = UserCreate(
            email="user1@example.com",
            username="user1",
            password="TestPass123!",
            confirm_password="TestPass123!",
            full_name="User One"
        )
        user1 = await service.create_user(user1_data)
        
        user2_data = UserCreate(
            email="user2@example.com", 
            username="user2",
            password="TestPass123!",
            confirm_password="TestPass123!",
            full_name="User Two"
        )
        user2 = await service.create_user(user2_data)
        
        # Update user1 successfully
        update_data = UserUpdate(
            email="user1_updated@example.com",
            username="user1_updated",
            full_name="User One Updated"
        )
        updated_user = await service.update_user(user1.id, update_data)
        assert updated_user.email == "user1_updated@example.com"
        assert updated_user.username == "user1_updated"
        assert updated_user.full_name == "User One Updated"
        
        # Try to update user2 with user1's new email (should fail)
        conflict_data = UserUpdate(email="user1_updated@example.com")
        with pytest.raises(ConflictError, match="Email .* is already in use"):
            await service.update_user(user2.id, conflict_data)
            
        # Try to update user2 with user1's new username (should fail) 
        conflict_data = UserUpdate(username="user1_updated")
        with pytest.raises(ConflictError, match="Username .* is already taken"):
            await service.update_user(user2.id, conflict_data)

    @pytest.mark.asyncio
    async def test_password_update_with_real_hashing(self, async_db_session: AsyncSession, sample_user_in_db):
        """Test password updates with real password hashing and verification."""
        service = UserService(async_db_session)
        
        password_data = UserPasswordUpdate(
            current_password="TestPass123!",
            new_password="NewTestPass456!",
            confirm_new_password="NewTestPass456!"
        )
        
        # Update password
        updated_user = await service.update_password(sample_user_in_db.id, password_data)
        assert updated_user.id == sample_user_in_db.id
        
        # Verify old password no longer works
        with pytest.raises(AuthenticationError):
            await service.authenticate_user(sample_user_in_db.username, "TestPass123!")
            
        # Verify new password works
        authenticated_user = await service.authenticate_user(sample_user_in_db.username, "NewTestPass456!")
        assert authenticated_user.id == sample_user_in_db.id
        
        # Test wrong current password
        wrong_password_data = UserPasswordUpdate(
            current_password="WrongCurrentPass!",
            new_password="AnotherNewPass789!",
            confirm_new_password="AnotherNewPass789!"
        )
        
        with pytest.raises(AuthenticationError, match="Current password is incorrect"):
            await service.update_password(sample_user_in_db.id, wrong_password_data)

    @pytest.mark.asyncio
    async def test_user_deletion_with_database_operations(self, async_db_session: AsyncSession):
        """Test user deletion with real database operations."""
        service = UserService(async_db_session)
        
        # Create user to delete
        user_data = UserCreate(
            email="todelete@example.com",
            username="todelete",
            password="TestPass123!",
            confirm_password="TestPass123!",
            full_name="To Delete User"
        )
        created_user = await service.create_user(user_data)
        user_id = created_user.id
        
        # Verify user exists
        user = await service.get_user(user_id)
        assert user.email == "todelete@example.com"
        
        # Delete user
        result = await service.delete_user(user_id)
        assert result is True
        
        # Verify user no longer exists
        with pytest.raises(NotFoundError, match=f"User with ID {user_id} not found"):
            await service.get_user(user_id)
        
        # Try to delete non-existent user
        with pytest.raises(NotFoundError, match="User with ID 99999 not found"):
            await service.delete_user(99999)

    @pytest.mark.asyncio
    async def test_pagination_with_real_database_data(self, async_db_session: AsyncSession):
        """Test pagination with actual database records and queries."""
        service = UserService(async_db_session)
        
        # Create multiple users with known data
        users_created = []
        for i in range(15):  # Create 15 users
            suffix = chr(65 + (i % 26))
            user_data = UserCreate(
                email=f"paginated{i:02d}@example.com",
                username=f"paginated{i:02d}",
                password="TestPass123!",
                confirm_password="TestPass123!",
                full_name=f"Paginated User {suffix}"
            )
            user = await service.create_user(user_data)
            users_created.append(user)
        
        # Test first page
        params = PaginationParams(skip=0, limit=5)
        result = await service.get_users_paginated(params)
        
        assert len(result.items) == 5
        assert result.total >= 15  # At least our 15 users (may have others from fixtures)
        assert result.page == 1
        assert result.total_pages >= 3
        
        # Test second page
        params = PaginationParams(skip=5, limit=5)
        result = await service.get_users_paginated(params)
        
        assert len(result.items) == 5
        assert result.page == 2
        
        # Test filtering by active status
        from app.schemas.pagination import FilterParams
        filter_params = FilterParams(is_active=True)
        params = PaginationParams(skip=0, limit=10, filters=filter_params)
        result = await service.get_users_paginated(params)
        
        # All our created users should be active
        assert len(result.items) == min(result.total, params.limit)
        for user in result.items:
            assert user.is_active is True

    @pytest.mark.asyncio
    async def test_search_functionality_with_real_queries(self, async_db_session: AsyncSession):
        """Test search with real database queries and LIKE operations."""
        service = UserService(async_db_session)
        
        # Create users with searchable content
        search_users = [
            ("john.doe@example.com", "johndoe", "John Doe"),
            ("jane.smith@example.com", "janesmith", "Jane Smith"),
            ("bob.johnson@example.com", "bobjohnson", "Bob Johnson"),
            ("alice.wonderland@example.com", "alicew", "Alice Wonderland"),
            ("charlie.brown@example.com", "charlieb", "Charlie Brown")
        ]
        
        created_users = []
        for email, username, full_name in search_users:
            user_data = UserCreate(
                email=email,
                username=username,
                password="TestPass123!",
                confirm_password="TestPass123!",
                full_name=full_name
            )
            user = await service.create_user(user_data)
            created_users.append(user)
        
        # Search by name
        search_params = SearchParams(query="john", skip=0, limit=10)
        result = await service.search_users(search_params)
        
        # Should find both "John Doe" and "Bob Johnson"
        assert len(result.items) >= 2
        found_names = [user.full_name for user in result.items]
        assert any("John" in name for name in found_names)
        assert any("Johnson" in name for name in found_names)
        
        # Search by email domain
        search_params = SearchParams(query="alice", skip=0, limit=10)
        result = await service.search_users(search_params)
        
        # Should find Alice Wonderland
        assert len(result.items) >= 1
        found_users = [user for user in result.items if "alice" in user.username.lower() or "Alice" in user.full_name]
        assert len(found_users) >= 1
        
        # Search by username
        search_params = SearchParams(query="smith", skip=0, limit=10)
        result = await service.search_users(search_params)
        
        # Should find Jane Smith
        assert len(result.items) >= 1
        found_users = [user for user in result.items if "smith" in user.username.lower() or "Smith" in user.full_name]
        assert len(found_users) >= 1

    @pytest.mark.asyncio
    async def test_concurrent_operations_race_conditions(self, async_db_session: AsyncSession):
        """Test concurrent operations that might cause race conditions in real database."""
        service = UserService(async_db_session)
        
        # Test concurrent user creation with same email
        async def create_user_with_email(email: str, index: int):
            try:
                user_data = UserCreate(
                    email=email,
                    username=f"concurrent_user_{index}_{id(asyncio.current_task())}",  # Unique username
                    password="TestPass123!",
                    confirm_password="TestPass123!",
                    full_name=f"Concurrent User {chr(65 + index)}"
                )
                return await service.create_user(user_data)
            except Exception as e:
                return e
        
        # Run 5 concurrent operations trying to create users with same email
        email = "concurrent@example.com"
        tasks = [create_user_with_email(email, i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At most one should succeed, others should fail with ConflictError
        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) <= 1, f"Expected at most 1 success, got {len(successes)}"
        assert len(failures) >= 4, f"Expected at least 4 failures, got {len(failures)}"

        if successes:
            successful_user = successes[0]
            assert successful_user.email == email

        for failure in failures:
            assert isinstance(failure, (ConflictError, ValidationError))
            assert any(keyword in str(failure) for keyword in {"already", "transaction"})

    @pytest.mark.asyncio
    async def test_date_range_queries_with_real_dates(self, async_db_session: AsyncSession):
        """Test date range queries with real database operations."""
        service = UserService(async_db_session)
        
        # Create users and manipulate their creation dates
        from app.models.user import User
        from datetime import datetime, timezone
        
        base_date = datetime.now(timezone.utc)
        
        # Create users for different date ranges
        old_user_data = User(
            username="olduser",
            email="old@example.com",
            full_name="Old User",
            hashed_password=service._hash_password("TestPass123!"),  
            is_active=True,
            is_superuser=False,
            created_at=base_date - timedelta(days=10),
            updated_at=base_date - timedelta(days=10)
        )
        async_db_session.add(old_user_data)
        
        recent_user_data = User(
            username="recentuser",
            email="recent@example.com",
            full_name="Recent User",
            hashed_password=service._hash_password("TestPass123!"),
            is_active=True,
            is_superuser=False,
            created_at=base_date - timedelta(days=2),
            updated_at=base_date - timedelta(days=2)
        )
        async_db_session.add(recent_user_data)
        
        await async_db_session.commit()
        await async_db_session.refresh(old_user_data)
        await async_db_session.refresh(recent_user_data)
        
        # Test date range query
        date_params = DateRangeParams(
            start_date=(base_date - timedelta(days=5)).isoformat(),
            end_date=base_date.isoformat()
        )
        pagination_params = PaginationParams(skip=0, limit=10)
        
        result = await service.get_users_by_date_range(date_params, pagination_params)
        
        # Should find the recent user but not the old user
        found_usernames = [user.username for user in result.items]
        assert "recentuser" in found_usernames
        assert "olduser" not in found_usernames
        
        # Test wider date range
        date_params = DateRangeParams(
            start_date=(base_date - timedelta(days=15)).isoformat(),
            end_date=base_date.isoformat()
        )
        result = await service.get_users_by_date_range(date_params, pagination_params)
        
        # Should find both users
        found_usernames = [user.username for user in result.items]
        assert "recentuser" in found_usernames
        assert "olduser" in found_usernames
