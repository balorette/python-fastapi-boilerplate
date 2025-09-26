"""Models package initialization.

Import model modules here so metadata-based operations (e.g. migrations,
table creation) always see the latest schema definitions.
"""

from app.models.user import User

__all__ = ["User"]
