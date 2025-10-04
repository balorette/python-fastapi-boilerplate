"""Enhanced user schemas with comprehensive validation."""

import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.role import RoleRead


class UserBase(BaseModel):
    """Base user schema with enhanced validation."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Unique username"
    )
    email: EmailStr = Field(..., description="Valid email address")
    full_name: str | None = Field(None, max_length=255, description="User's full name")
    is_active: bool = Field(True, description="Whether the user account is active")
    is_superuser: bool = Field(
        False, description="Whether the user has admin privileges"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores, and hyphens"
            )
        if v.lower() in ["root", "api", "test", "user"]:
            raise ValueError("Username is reserved")
        return v.lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        """Validate full name format."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if not re.match(r"^[a-zA-Z\s\'-]+$", v):
                raise ValueError(
                    "Full name can only contain letters, spaces, apostrophes, and hyphens"
                )
        return v


class UserCreate(UserBase):
    """Schema for user creation with password requirements."""

    password: str = Field(
        ..., min_length=8, max_length=128, description="Strong password"
    )
    confirm_password: str = Field(..., description="Password confirmation")
    role_names: list[str] | None = Field(
        None, description="Optional list of role names to assign"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_password_match(cls, v, info):
        """Ensure password confirmation matches."""
        if info.data and "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "is_active": True,
                "is_superuser": False,
                "role_names": ["member"],
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for user updates with optional fields."""

    username: str | None = Field(None, min_length=3, max_length=50)
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    role_names: list[str] | None = Field(
        None, description="Optional list of role names to assign"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format if provided."""
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_-]+$", v):
                raise ValueError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
            if v.lower() in ["admin", "root", "api", "test", "user"]:
                raise ValueError("Username is reserved")
            return v.lower()
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        """Validate full name format if provided."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            if not re.match(r"^[a-zA-Z\s\'-]+$", v):
                raise ValueError(
                    "Full name can only contain letters, spaces, apostrophes, and hyphens"
                )
        return v


class UserPasswordUpdate(BaseModel):
    """Schema for password updates."""

    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New strong password"
    )
    confirm_new_password: str = Field(..., description="New password confirmation")

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("confirm_new_password")
    @classmethod
    def validate_password_match(cls, v, info):
        """Ensure password confirmation matches."""
        if info.data and "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class UserResponse(UserBase):
    """Complete user schema for responses."""

    id: int = Field(..., description="Unique user ID")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    roles: list[RoleRead] = Field(
        default_factory=list, description="Roles assigned to the user"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """Schema for authentication token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class TokenData(BaseModel):
    """Schema for token data."""

    username: str | None = Field(None, description="Username from token")


class UserSearchParams(BaseModel):
    """Schema for user search parameters."""

    query: str = Field(..., min_length=1, max_length=255, description="Search query")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum records to return")
    active_only: bool = Field(False, description="Search only active users")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        """Sanitize search query."""
        return v.strip()


class UserStats(BaseModel):
    """Schema for user statistics."""

    total_users: int = Field(..., ge=0, description="Total number of users")
    active_users: int = Field(..., ge=0, description="Number of active users")
    inactive_users: int = Field(..., ge=0, description="Number of inactive users")
    superusers: int = Field(..., ge=0, description="Number of superusers")
    recent_registrations: int = Field(
        ..., ge=0, description="Recent registrations (last 30 days)"
    )
