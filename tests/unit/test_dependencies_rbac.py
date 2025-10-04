"""Unit tests for RBAC dependency factories."""

import pytest
from fastapi import HTTPException

from app.api.dependencies import require_permissions, require_roles
from app.core.authz import SystemPermission, SystemRole


class DummyUser:
    """Simple stand-in for `app.models.user.User` with RBAC attributes."""

    def __init__(
        self,
        *,
        roles: set[str] | None = None,
        permissions: set[str] | None = None,
        is_active: bool = True,
    ) -> None:
        self.role_names = {role.lower() for role in roles or set()}
        self.permission_names = {perm.lower() for perm in permissions or set()}
        self.is_active = is_active


@pytest.mark.asyncio
async def test_require_roles_allows_user_with_any_matching_role() -> None:
    guard = require_roles(SystemRole.ADMIN, "manager")
    user = DummyUser(roles={"manager"})

    result = await guard(user)

    assert result is user


@pytest.mark.asyncio
async def test_require_roles_rejects_user_without_required_role() -> None:
    guard = require_roles(SystemRole.ADMIN)
    user = DummyUser(roles={"member"})

    with pytest.raises(HTTPException) as exc_info:
        await guard(user)

    assert exc_info.value.status_code == 403
    assert "role" in exc_info.value.detail.lower()


def test_require_roles_raises_value_error_when_no_roles_provided() -> None:
    with pytest.raises(ValueError):
        require_roles()


@pytest.mark.asyncio
async def test_require_permissions_allows_user_with_all_permissions() -> None:
    guard = require_permissions(SystemPermission.USERS_MANAGE, "manage-projects")
    user = DummyUser(
        permissions={
            SystemPermission.USERS_MANAGE.value,
            "manage-projects",
            "view-reports",
        }
    )

    result = await guard(user)

    assert result is user


@pytest.mark.asyncio
async def test_require_permissions_rejects_user_missing_permissions() -> None:
    guard = require_permissions("users:manage", "manage-projects")
    user = DummyUser(permissions={"users:manage"})

    with pytest.raises(HTTPException) as exc_info:
        await guard(user)

    assert exc_info.value.status_code == 403
    assert "permission" in exc_info.value.detail.lower()


def test_require_permissions_raises_value_error_when_no_permissions_provided() -> None:
    with pytest.raises(ValueError):
        require_permissions()
