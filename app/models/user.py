"""Enhanced User model with additional fields."""


from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Enhanced User model with comprehensive fields."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(default=None)  # Optional for OAuth users
    full_name: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    # OAuth fields
    oauth_provider: Mapped[str | None] = mapped_column(default=None)  # 'google', 'local', etc.
    oauth_id: Mapped[str | None] = mapped_column(default=None)  # External provider user ID
    oauth_email_verified: Mapped[bool | None] = mapped_column(default=None)  # Email verification status from provider
    oauth_refresh_token: Mapped[str | None] = mapped_column(default=None)  # For future API calls
