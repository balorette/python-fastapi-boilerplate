"""Pydantic schemas for roles and permissions."""

from pydantic import BaseModel, ConfigDict, Field


class PermissionRead(BaseModel):
    """Read schema for permissions."""

    id: int = Field(..., description="Permission identifier")
    name: str = Field(..., description="Unique permission name")
    description: str | None = Field(None, description="Permission description")

    model_config = ConfigDict(from_attributes=True)


class RoleRead(BaseModel):
    """Read schema for roles."""

    id: int = Field(..., description="Role identifier")
    name: str = Field(..., description="Unique role name")
    description: str | None = Field(None, description="Role description")
    permissions: list[PermissionRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
