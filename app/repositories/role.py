"""Repositories for role and permission models."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Repository for working with role models."""

    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.name == name)
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_names(self, names: list[str]) -> list[Role]:
        if not names:
            return []

        stmt = (
            select(Role)
            .where(Role.name.in_(names))
            .options(selectinload(Role.permissions))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PermissionRepository(BaseRepository[Permission]):
    """Repository for permission models."""

    def __init__(self, session: AsyncSession):
        super().__init__(Permission, session)

    async def get_by_name(self, name: str) -> Permission | None:
        stmt = select(Permission).where(Permission.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
