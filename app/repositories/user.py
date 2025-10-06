"""User repository for user-specific database operations."""

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Enhanced User repository with search and advanced filtering."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    def _with_role_hierarchy(
        self,
        stmt: Select,
        load_role_hierarchy: bool,
    ) -> Select:
        """Optionally eager load user roles and nested permissions."""

        if not load_role_hierarchy:
            return stmt
        return stmt.options(selectinload(User.roles).selectinload(Role.permissions))

    async def get_by_email(
        self,
        email: str,
        *,
        load_role_hierarchy: bool = False,
    ) -> User | None:
        """Get user by email address."""

        stmt = select(User).where(User.email == email)
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(
        self,
        username: str,
        *,
        load_role_hierarchy: bool = False,
    ) -> User | None:
        """Get user by username."""

        stmt = select(User).where(User.username == username)
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
        *,
        load_role_hierarchy: bool = False,
    ) -> list[User]:
        """Search users by username or email with fuzzy matching."""
        search_term = f"%{query}%"
        stmt = select(User).where(
            or_(User.username.ilike(search_term), User.email.ilike(search_term))
        )
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        *,
        load_role_hierarchy: bool = False,
    ) -> list[User]:
        """Get all active users with optional ordering."""
        stmt = select(User).where(User.is_active.is_(True))
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)

        # Apply ordering
        if order_by:
            if order_by.startswith("-"):
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

    async def get_users_by_creation_date(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        skip: int = 0,
        limit: int = 100,
        *,
        load_role_hierarchy: bool = False,
    ) -> list[User]:
        """Get users created within a date range."""
        stmt = select(User)
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)

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
            skip=skip, limit=limit, filters={"is_superuser": True}
        )

    # OAuth-specific methods

    async def get_by_oauth_id(
        self,
        oauth_provider: str,
        oauth_id: str,
        *,
        load_role_hierarchy: bool = False,
    ) -> User | None:
        """Get user by OAuth provider and ID."""

        stmt = select(User).where(
            and_(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
        )
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_oauth_users(
        self,
        oauth_provider: str,
        skip: int = 0,
        limit: int = 100,
        *,
        load_role_hierarchy: bool = False,
    ) -> list[User]:
        """Get users by OAuth provider."""

        stmt = select(User).where(User.oauth_provider == oauth_provider)
        stmt = self._with_role_hierarchy(stmt, load_role_hierarchy)
        stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
