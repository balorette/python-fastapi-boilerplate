"""Enhanced user service with comprehensive business logic."""

from datetime import UTC
from typing import Any

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.oauth import GoogleUserInfo, OAuthUserCreate
from app.schemas.pagination import (
    DateRangeParams,
    PaginatedResponse,
    PaginationParams,
    SearchParams,
)
from app.schemas.user import UserCreate, UserPasswordUpdate, UserResponse, UserUpdate

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Enhanced user service with comprehensive business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def _derive_username_seed(self, value: str) -> str:
        """Create a base username seed from an email or raw username."""
        base = value.split("@")[0] if "@" in value else value
        return base.lower()

    async def _ensure_unique_username(self, seed: str) -> str:
        """Ensure the generated username is unique, appending a suffix if needed."""
        candidate = seed
        suffix = 1
        while await self.repository.username_exists(candidate):
            candidate = f"{seed}{suffix}"
            suffix += 1
        return candidate

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with validation."""
        # Check if email already exists
        if await self.repository.email_exists(user_data.email):
            raise ConflictError(f"Email {user_data.email} is already registered")

        # Check if username already exists
        if await self.repository.username_exists(user_data.username):
            raise ConflictError(f"Username {user_data.username} is already taken")

        # Create user data
        user_dict = user_data.model_dump(exclude={'password', 'confirm_password'})
        user_dict['hashed_password'] = self._hash_password(user_data.password)

        try:
            return await self.repository.create(user_dict)
        except Exception as e:
            raise ValidationError(f"Failed to create user: {str(e)}")

    async def get_user(self, user_id: int, load_relationships: bool = False) -> User:
        """Get a user by ID."""
        user = await self.repository.get(user_id, load_relationships=load_relationships)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        return user

    async def get_user_by_email(self, email: str) -> User:
        """Get a user by email."""
        user = await self.repository.get_by_email(email)
        if not user:
            raise NotFoundError(f"User with email {email} not found")
        return user

    async def get_user_by_username(self, username: str) -> User:
        """Get a user by username."""
        user = await self.repository.get_by_username(username)
        if not user:
            raise NotFoundError(f"User with username {username} not found")
        return user

    async def get_users_paginated(
        self,
        params: PaginationParams,
        filters: dict[str, Any] | None = None
    ) -> PaginatedResponse[UserResponse]:
        """Get paginated list of users."""
        # Get total count
        total = await self.repository.count_records(filters)

        # Get users
        users = await self.repository.get_multi(
            skip=params.skip,
            limit=params.limit,
            filters=filters,
            order_by=params.order_by
        )

        # Convert to response schema
        user_responses = [UserResponse.model_validate(user) for user in users]

        return PaginatedResponse.create(
            items=user_responses,
            total=total,
            skip=params.skip,
            limit=params.limit
        )

    async def search_users(self, params: SearchParams) -> PaginatedResponse[UserResponse]:
        """Search users with pagination."""
        # Count search results
        search_users = await self.repository.search_users(
            query=params.query,
            skip=0,
            limit=10000  # Get all for counting
        )
        total = len(search_users)

        # Get paginated results
        users = await self.repository.search_users(
            query=params.query,
            skip=params.skip,
            limit=params.limit
        )

        # Convert to response schema
        user_responses = [UserResponse.model_validate(user) for user in users]

        return PaginatedResponse.create(
            items=user_responses,
            total=total,
            skip=params.skip,
            limit=params.limit
        )

    async def get_active_users_paginated(
        self,
        params: PaginationParams
    ) -> PaginatedResponse[UserResponse]:
        """Get paginated list of active users."""
        # Count active users
        total = await self.repository.count_active_users()

        # Get active users
        users = await self.repository.get_active_users(
            skip=params.skip,
            limit=params.limit,
            order_by=params.order_by
        )

        # Convert to response schema
        user_responses = [UserResponse.model_validate(user) for user in users]

        return PaginatedResponse.create(
            items=user_responses,
            total=total,
            skip=params.skip,
            limit=params.limit
        )

    async def get_users_by_date_range(
        self,
        date_params: DateRangeParams,
        pagination_params: PaginationParams
    ) -> PaginatedResponse[UserResponse]:
        """Get users created within a date range."""
        # Count users in date range
        filters = {}
        if date_params.start_date:
            filters['created_at'] = {'gte': date_params.start_date}
        if date_params.end_date:
            if 'created_at' in filters:
                filters['created_at']['lte'] = date_params.end_date
            else:
                filters['created_at'] = {'lte': date_params.end_date}

        total = await self.repository.count_records(filters)

        # Get users
        users = await self.repository.get_users_by_creation_date(
            start_date=date_params.start_date,
            end_date=date_params.end_date,
            skip=pagination_params.skip,
            limit=pagination_params.limit
        )

        # Convert to response schema
        user_responses = [UserResponse.model_validate(user) for user in users]

        return PaginatedResponse.create(
            items=user_responses,
            total=total,
            skip=pagination_params.skip,
            limit=pagination_params.limit
        )

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """Update a user with validation."""
        user = await self.get_user(user_id)

        update_dict = user_data.model_dump(exclude_unset=True)

        # Validate email uniqueness if being updated
        if 'email' in update_dict:
            if await self.repository.email_exists(update_dict['email'], exclude_id=user_id):
                raise ConflictError(f"Email {update_dict['email']} is already in use")

        # Validate username uniqueness if being updated
        if 'username' in update_dict:
            if await self.repository.username_exists(update_dict['username'], exclude_id=user_id):
                raise ConflictError(f"Username {update_dict['username']} is already taken")

        try:
            return await self.repository.update(user, update_dict)
        except Exception as e:
            raise ValidationError(f"Failed to update user: {str(e)}")

    async def update_password(self, user_id: int, password_data: UserPasswordUpdate) -> User:
        """Update user password with current password verification."""
        user = await self.get_user(user_id)

        # Check if user has a local password (not OAuth-only)
        if not user.hashed_password:
            raise ValidationError("Cannot update password for OAuth-only users")

        # Verify current password
        if not self._verify_password(password_data.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        # Update password
        update_dict = {'hashed_password': self._hash_password(password_data.new_password)}

        try:
            return await self.repository.update(user, update_dict)
        except Exception as e:
            raise ValidationError(f"Failed to update password: {str(e)}")

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        if not await self.repository.record_exists(user_id):
            raise NotFoundError(f"User with ID {user_id} not found")

        try:
            return await self.repository.delete(user_id)
        except Exception as e:
            raise ValidationError(f"Failed to delete user: {str(e)}")

    async def activate_user(self, user_id: int) -> User:
        """Activate a user account."""
        user = await self.get_user(user_id)
        if user.is_active:
            return user  # Already active

        return await self.repository.update(user, {'is_active': True})

    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account."""
        user = await self.get_user(user_id)
        if not user.is_active:
            return user  # Already inactive

        return await self.repository.update(user, {'is_active': False})

    async def authenticate_user(self, username: str, password: str) -> User:
        """Authenticate a user by username/email and password."""
        # Try to get user by username first, then by email
        user = await self.repository.get_by_username(username)
        if not user:
            user = await self.repository.get_by_email(username)

        # Check if user exists and has a local password
        if not user:
            raise AuthenticationError("Invalid credentials")

        if not user.hashed_password:
            raise AuthenticationError("This account uses OAuth login. Please use Google Sign-In.")

        if not self._verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            raise AuthenticationError("User account is deactivated")

        return user

    # OAuth-specific methods

    async def create_oauth_user(self, oauth_data: OAuthUserCreate) -> User:
        """Create a new user from OAuth provider data."""
        # Check if user already exists by email (auto-link accounts)
        existing_user = await self.repository.get_by_email(oauth_data.email)

        if existing_user:
            # Link OAuth account to existing user
            return await self.link_oauth_account(existing_user.id, oauth_data)

        username_seed = self._derive_username_seed(oauth_data.username or oauth_data.email)
        unique_username = await self._ensure_unique_username(username_seed)

        user_dict = oauth_data.model_dump()
        user_dict['username'] = unique_username

        try:
            user = await self.repository.create(user_dict)
            await self.session.commit()
            return user
        except Exception as e:
            await self.session.rollback()
            raise ConflictError(f"Failed to create OAuth user: {str(e)}")

    async def link_oauth_account(self, user_id: int, oauth_data: OAuthUserCreate) -> User:
        """Link OAuth provider to existing user account."""
        user = await self.get_user(user_id)

        # Update user with OAuth information
        update_data = {
            'oauth_provider': oauth_data.oauth_provider,
            'oauth_id': oauth_data.oauth_id,
            'oauth_email_verified': oauth_data.oauth_email_verified,
            'oauth_refresh_token': oauth_data.oauth_refresh_token,
            # Update name if not set or if OAuth provides more complete info
            'full_name': oauth_data.full_name if not user.full_name else user.full_name
        }

        try:
            updated_user = await self.repository.update(user, update_data)
            await self.session.commit()
            return updated_user
        except Exception as e:
            await self.session.rollback()
            raise ConflictError(f"Failed to link OAuth account: {str(e)}")

    async def get_by_oauth_id(self, oauth_provider: str, oauth_id: str) -> User | None:
        """Get user by OAuth provider and ID."""
        return await self.repository.get_by_oauth_id(oauth_provider, oauth_id)

    async def create_or_update_oauth_user(self, google_user_info: GoogleUserInfo, refresh_token: str | None = None) -> tuple[User, bool]:
        """Create or update user from Google OAuth info.
        
        Returns:
            tuple: (user, is_new_user)
        """
        # First try to find by OAuth ID
        existing_user = await self.get_by_oauth_id("google", google_user_info.id)

        if existing_user:
            # Update existing OAuth user
            update_data = {
                'full_name': google_user_info.name,
                'oauth_email_verified': google_user_info.verified_email,
                'oauth_refresh_token': refresh_token,
                'is_active': True  # Reactivate if deactivated
            }

            try:
                updated_user = await self.repository.update(existing_user, update_data)
                await self.session.commit()
                return updated_user, False
            except Exception as e:
                await self.session.rollback()
                raise ConflictError(f"Failed to update OAuth user: {str(e)}")

        # Create OAuth user data
        oauth_user_data = OAuthUserCreate(
            email=google_user_info.email,
            username=await self._ensure_unique_username(
                self._derive_username_seed(google_user_info.email)
            ),
            full_name=google_user_info.name,
            oauth_provider="google",
            oauth_id=google_user_info.id,
            oauth_email_verified=google_user_info.verified_email,
            oauth_refresh_token=refresh_token,
            is_active=True,
            is_superuser=False
        )

        # Create or link user
        user = await self.create_oauth_user(oauth_user_data)
        return user, True

    async def authenticate_oauth_user(self, oauth_provider: str, oauth_id: str) -> User:
        """Authenticate a user via OAuth provider."""
        user = await self.get_by_oauth_id(oauth_provider, oauth_id)

        if not user:
            raise AuthenticationError(f"No user found for {oauth_provider} ID: {oauth_id}")

        if not user.is_active:
            raise AuthenticationError("User account is deactivated")

        return user

    async def get_user_stats(self) -> dict[str, int]:
        """Get user statistics."""
        total_users = await self.repository.count_records()
        active_users = await self.repository.count_active_users()
        inactive_users = total_users - active_users
        superusers = await self.repository.count_records({'is_superuser': True})

        # Recent registrations (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        recent_registrations = await self.repository.count_records({
            'created_at': {'gte': thirty_days_ago}
        })

        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'superusers': superusers,
            'recent_registrations': recent_registrations
        }
