"""User repository for user-specific database operations."""

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Enhanced User repository with search and advanced filtering."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """Search users by username or email with fuzzy matching."""
        search_term = f"%{query}%"
        stmt = select(User).where(
            or_(
                User.username.ilike(search_term),
                User.email.ilike(search_term)
            )
        ).offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None
    ) -> list[User]:
        """Get all active users with optional ordering."""
        stmt = select(User).where(User.is_active == True)

        # Apply ordering
        if order_by:
            if order_by.startswith('-'):
                # Descending order
                order_field = order_by[1:]
                if hasattr(User, order_field):
                    stmt = stmt.order_by(getattr(User, order_field).desc())
            else:
                # Ascending order
                if hasattr(User, order_by):
                    stmt = stmt.order_by(getattr(User, order_by))
        else:
            stmt = stmt.order_by(User.created_at.desc())

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def email_exists(self, email: str, exclude_id: int | None = None) -> bool:
        """Check if email exists, optionally excluding a specific user ID."""
        stmt = select(User.id).where(User.email == email)
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str, exclude_id: int | None = None) -> bool:
        """Check if username exists, optionally excluding a specific user ID."""
        stmt = select(User.id).where(User.username == username)
        if exclude_id:
            stmt = stmt.where(User.id != exclude_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count_active_users(self) -> int:
        """Count active users."""
        stmt = select(func.count()).select_from(User).where(User.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_users_by_creation_date(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[User]:
        """Get users created within a date range."""
        stmt = select(User)

        conditions = []
        if start_date:
            conditions.append(User.created_at >= start_date)
        if end_date:
            conditions.append(User.created_at <= end_date)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_superusers(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get superuser accounts."""
        return await self.get_multi(
            skip=skip,
            limit=limit,
            filters={"is_superuser": True}
        )

    # OAuth-specific methods

    async def get_by_oauth_id(self, oauth_provider: str, oauth_id: str) -> User | None:
        """Get user by OAuth provider and ID."""
        stmt = select(User).where(
            and_(
                User.oauth_provider == oauth_provider,
                User.oauth_id == oauth_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_oauth_users(self, oauth_provider: str, skip: int = 0, limit: int = 100) -> list[User]:
        """Get users by OAuth provider."""
        stmt = select(User).where(User.oauth_provider == oauth_provider)
        stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_oauth_users(self, oauth_provider: str) -> int:
        """Count users by OAuth provider."""
        stmt = select(func.count(User.id)).where(User.oauth_provider == oauth_provider)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
