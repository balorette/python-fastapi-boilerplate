"""Enhanced User model with additional fields."""

from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Enhanced User model with comprehensive fields."""
    
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    full_name: Mapped[Optional[str]] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)