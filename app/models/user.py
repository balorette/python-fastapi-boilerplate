"""Example User model."""

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)