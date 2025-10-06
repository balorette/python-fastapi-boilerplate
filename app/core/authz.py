"""Authorization utilities including system roles, permissions, and seed helpers."""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role


class SystemPermission(str, Enum):
    """Canonical permission names used across the application."""

    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"


class SystemRole(str, Enum):
    """Canonical role names used across the application."""

    ADMIN = "admin"
    MEMBER = "member"


# Mapping of roles to the permissions that should be granted by default.
DEFAULT_ROLE_PERMISSIONS: dict[SystemRole, tuple[SystemPermission, ...]] = {
    SystemRole.ADMIN: (
        SystemPermission.USERS_READ,
        SystemPermission.USERS_MANAGE,
    ),
    SystemRole.MEMBER: (SystemPermission.USERS_READ,),
}


async def ensure_default_roles(session: AsyncSession) -> None:
    """Ensure the default roles and permissions exist in the database."""

    existing_permissions = {
        name: perm for name, perm in await _fetch_existing_permissions(session)
    }

    for permission in SystemPermission:
        if permission.value not in existing_permissions:
            session.add(
                Permission(name=permission.value, description=permission.name.title())
            )

    await session.flush()

    existing_roles = {name: role for name, role in await _fetch_existing_roles(session)}

    for role in SystemRole:
        if role.value not in existing_roles:
            session.add(
                Role(name=role.value, description=f"System role: {role.name.title()}")
            )

    await session.flush()

    # Refresh role assignments to ensure permissions are linked correctly.
    permission_lookup = {
        permission.name: permission
        for permission in await _fetch_all_permissions(session)
    }
    role_lookup = {role.name: role for role in await _fetch_all_roles(session)}

    for role, permissions in DEFAULT_ROLE_PERMISSIONS.items():
        db_role = role_lookup[role.value]
        desired_permission_names = {permission.value for permission in permissions}
        current_permission_names = {perm.name for perm in db_role.permissions}

        if desired_permission_names - current_permission_names:
            db_role.permissions = [
                permission_lookup[name] for name in desired_permission_names
            ]

    await session.commit()


async def _fetch_existing_permissions(
    session: AsyncSession,
) -> list[tuple[str, Permission]]:
    result = await session.execute(select(Permission))
    return [(permission.name, permission) for permission in result.scalars().all()]


async def _fetch_existing_roles(session: AsyncSession) -> list[tuple[str, Role]]:
    result = await session.execute(select(Role))
    return [(role.name, role) for role in result.scalars().all()]


async def _fetch_all_permissions(session: AsyncSession) -> Iterable[Permission]:
    result = await session.execute(select(Permission))
    return result.scalars().all()


async def _fetch_all_roles(session: AsyncSession) -> Iterable[Role]:
    result = await session.execute(select(Role))
    return result.scalars().all()
