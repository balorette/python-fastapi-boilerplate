"""OAuth-specific Pydantic schemas."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GoogleUserInfo(BaseModel):
    """Google user information from OAuth."""
    
    id: str = Field(..., description="Google user ID")
    email: EmailStr = Field(..., description="User email")
    verified_email: bool = Field(..., description="Email verification status")
    name: str = Field(..., description="Full name")
    given_name: str = Field(..., description="First name")
    family_name: str = Field(..., description="Last name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    locale: Optional[str] = Field(None, description="User locale")


class GoogleTokenResponse(BaseModel):
    """Google token response."""
    
    access_token: str = Field(..., description="Google access token")
    refresh_token: Optional[str] = Field(None, description="Google refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str = Field(..., description="Token scope")
    id_token: Optional[str] = Field(None, description="ID token")


class OAuthUserCreate(BaseModel):
    """Schema for creating OAuth users."""
    
    email: EmailStr
    username: str
    full_name: str
    oauth_provider: str = Field(..., description="OAuth provider (google, etc.)")
    oauth_id: str = Field(..., description="External provider user ID")
    oauth_email_verified: bool = Field(default=False, description="Email verification status")
    oauth_refresh_token: Optional[str] = Field(None, description="Refresh token for future API calls")
    is_active: bool = Field(default=True, description="User active status")
    is_superuser: bool = Field(default=False, description="Superuser status")


class OAuthLoginRequest(BaseModel):
    """OAuth login request."""
    
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")


class OAuthLoginResponse(BaseModel):
    """OAuth login response."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: dict = Field(..., description="User information")
    is_new_user: bool = Field(..., description="Whether this is a newly created user")


class GoogleAuthURL(BaseModel):
    """Google OAuth authorization URL response."""
    
    url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="CSRF protection state")