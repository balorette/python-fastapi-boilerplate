"""Enhanced User model with additional fields and RBAC helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover - import cycle protection for typing only
    from app.models.role import Role


class User(Base):
    """Enhanced User model with comprehensive fields."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(
        default=None
    )  # Optional for OAuth users
    full_name: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    # OAuth fields
    oauth_provider: Mapped[str | None] = mapped_column(
        default=None
    )  # 'google', 'local', etc.
    oauth_id: Mapped[str | None] = mapped_column(
        default=None
    )  # External provider user ID
    oauth_email_verified: Mapped[bool | None] = mapped_column(
        default=None
    )  # Email verification status from provider
    oauth_refresh_token: Mapped[str | None] = mapped_column(
        default=None
    )  # For future API calls

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )

    @property
    def role_names(self) -> list[str]:
        """Return the list of role names assigned to the user."""

        return [role.name for role in getattr(self, "roles", [])]

    @property
    def permission_names(self) -> list[str]:
        """Return the list of permission names derived from the user's roles."""

        permissions = {
            permission.name
            for role in getattr(self, "roles", [])
            for permission in getattr(role, "permissions", [])
        }
        return sorted(permissions)

    def has_role(self, role_name: str) -> bool:
        """Check if the user has a given role."""

        return role_name in self.role_names

    def has_permission(self, permission_name: str) -> bool:
        """Check if the user has a given permission."""

        return permission_name in self.permission_names
