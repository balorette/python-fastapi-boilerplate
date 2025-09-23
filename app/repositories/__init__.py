"""Repository layer for data access patterns."""

from .base import BaseRepository
from .user import UserRepository

__all__ = ["BaseRepository", "UserRepository"]