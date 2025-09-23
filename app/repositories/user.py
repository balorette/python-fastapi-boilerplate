"""User repository for user-specific database operations."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for User model with user-specific operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        stmt = select(User.id).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        stmt = select(User.id).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def get_active_users(self, skip: int = 0, limit: int = 100):
        """Get only active users."""
        return await self.get_multi(
            skip=skip, 
            limit=limit, 
            filters={"is_active": True}
        )
    
    async def get_superusers(self, skip: int = 0, limit: int = 100):
        """Get superuser accounts."""
        return await self.get_multi(
            skip=skip, 
            limit=limit, 
            filters={"is_superuser": True}
        )