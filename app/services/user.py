"""User service for business logic operations."""

from typing import List, Optional
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.user import UserRepository
from ..models.user import User
from ..schemas.user import UserCreate, UserUpdate
from ..core.exceptions import ValidationError


class UserService:
    """Service layer for user business logic."""

    def __init__(self, session: AsyncSession):
        self.repository = UserRepository(session)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def _get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return self.pwd_context.hash(password)

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with validation."""
        # Validate email uniqueness
        if await self.repository.email_exists(user_data.email):
            raise ValidationError("Email already registered")

        # Validate username uniqueness
        if await self.repository.username_exists(user_data.username):
            raise ValidationError("Username already taken")

        # Create user with hashed password
        user_dict = user_data.model_dump()
        user_dict["hashed_password"] = self._get_password_hash(user_data.password)
        del user_dict["password"]  # Remove plain password

        return await self.repository.create(user_dict)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.repository.get(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.repository.get_by_email(email)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.repository.get_by_username(username)

    async def get_users(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[User]:
        """Get users with optional filtering."""
        if active_only:
            return await self.repository.get_active_users(skip=skip, limit=limit)
        return await self.repository.get_multi(skip=skip, limit=limit)

    async def update_user(
        self, user_id: int, user_update: UserUpdate
    ) -> Optional[User]:
        """Update user information."""
        # Check if user exists
        existing_user = await self.repository.get(user_id)
        if not existing_user:
            return None

        update_dict = user_update.model_dump(exclude_unset=True)

        # Handle password update
        if "password" in update_dict:
            update_dict["hashed_password"] = self._get_password_hash(
                update_dict["password"]
            )
            del update_dict["password"]

        # Validate email uniqueness if changing email
        if "email" in update_dict and update_dict["email"] != existing_user.email:
            if await self.repository.email_exists(update_dict["email"]):
                raise ValidationError("Email already registered")

        # Validate username uniqueness if changing username
        if (
            "username" in update_dict
            and update_dict["username"] != existing_user.username
        ):
            if await self.repository.username_exists(update_dict["username"]):
                raise ValidationError("Username already taken")

        return await self.repository.update(user_id, update_dict)

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        return await self.repository.delete(user_id)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        user = await self.repository.get_by_email(email)
        if not user:
            return None
        if not self._verify_password(password, str(user.hashed_password)):
            return None
        return user

    async def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user account."""
        return await self.repository.update(user_id, {"is_active": True})

    async def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user account."""
        return await self.repository.update(user_id, {"is_active": False})

    async def make_superuser(self, user_id: int) -> Optional[User]:
        """Grant superuser privileges."""
        return await self.repository.update(user_id, {"is_superuser": True})

    async def remove_superuser(self, user_id: int) -> Optional[User]:
        """Remove superuser privileges."""
        return await self.repository.update(user_id, {"is_superuser": False})
