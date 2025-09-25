"""OAuth2-compliant schemas for authentication."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# OAuth2 Authorization Flow Schemas
class AuthorizationRequest(BaseModel):
    """OAuth2 authorization request parameters."""
    provider: str = Field(..., description="OAuth provider (local, google, etc.)")
    response_type: Literal["code"] = "code"
    client_id: str = Field(..., description="OAuth2 client ID")
    redirect_uri: str = Field(..., description="Callback URL")
    scope: str | None = Field(None, description="Requested scopes")
    state: str = Field(..., description="CSRF protection state")
    code_challenge: str | None = Field(None, description="PKCE code challenge")
    code_challenge_method: Literal["S256"] | None = Field(None, description="PKCE method")

    # Local auth fields (optional, only for provider="local")
    username: str | None = Field(None, description="Username for local auth")
    password: str | None = Field(None, description="Password for local auth")


class AuthorizationResponse(BaseModel):
    """OAuth2 authorization response."""
    authorization_url: str | None = Field(None, description="Provider authorization URL")
    authorization_code: str | None = Field(None, description="Authorization code (for local auth)")
    state: str = Field(..., description="CSRF state parameter")
    redirect_uri: str | None = Field(None, description="Redirect URI")
    code_verifier: str | None = Field(None, description="PKCE code verifier (store securely)")


class TokenRequest(BaseModel):
    """OAuth2 token exchange request."""
    provider: str = Field(..., description="OAuth provider (local, google, etc.)")
    grant_type: Literal["authorization_code", "refresh_token"] = "authorization_code"
    code: str | None = Field(None, description="Authorization code")
    redirect_uri: str | None = Field(None, description="Same redirect URI from authorization")
    client_id: str | None = Field(None, description="OAuth2 client ID")
    code_verifier: str | None = Field(None, description="PKCE code verifier")
    refresh_token: str | None = Field(None, description="Refresh token for renewal")


class TokenResponse(BaseModel):
    """OAuth2-compliant token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")
    refresh_token: str | None = Field(None, description="Refresh token")
    scope: str | None = Field(None, description="Granted scopes")


class LocalLoginRequest(BaseModel):
    """Local account login request."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password")
    grant_type: Literal["password"] = "password"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    grant_type: Literal["refresh_token"] = "refresh_token"
    refresh_token: str = Field(..., description="Valid refresh token")


class ErrorResponse(BaseModel):
    """OAuth2 error response."""
    error: str = Field(..., description="Error code")
    error_description: str | None = Field(None, description="Human-readable error description")
    error_uri: str | None = Field(None, description="URI to error documentation")


# Provider-Specific Schemas
class GoogleUserInfo(BaseModel):
    """Google user information from OAuth."""

    id: str = Field(..., description="Google user ID")
    email: EmailStr = Field(..., description="User email")
    verified_email: bool = Field(..., description="Email verification status")
    name: str = Field(..., description="Full name")
    given_name: str = Field(..., description="First name")
    family_name: str = Field(..., description="Last name")
    picture: str | None = Field(None, description="Profile picture URL")
    locale: str | None = Field(None, description="User locale")


class GoogleTokenResponse(BaseModel):
    """Google token response."""

    access_token: str = Field(..., description="Google access token")
    refresh_token: str | None = Field(None, description="Google refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str = Field(..., description="Token scope")
    id_token: str | None = Field(None, description="ID token")


class OAuthUserCreate(BaseModel):
    """Schema for creating OAuth users."""

    email: EmailStr
    username: str
    full_name: str
    oauth_provider: str = Field(..., description="OAuth provider (google, etc.)")
    oauth_id: str = Field(..., description="External provider user ID")
    oauth_email_verified: bool = Field(default=False, description="Email verification status")
    oauth_refresh_token: str | None = Field(None, description="Refresh token for future API calls")
    is_active: bool = Field(default=True, description="User active status")
    is_superuser: bool = Field(default=False, description="Superuser status")


# Legacy schemas for backward compatibility
class OAuthLoginRequest(BaseModel):
    """OAuth login request (legacy)."""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str | None = Field(None, description="State parameter for CSRF protection")


class OAuthLoginResponse(BaseModel):
    """OAuth login response (legacy)."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: dict = Field(..., description="User information")
    is_new_user: bool = Field(..., description="Whether this is a newly created user")


class GoogleAuthURL(BaseModel):
    """Google OAuth authorization URL response (legacy)."""

    url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="CSRF protection state")


# Compatibility alias
Token = TokenResponse
TokenData = TokenResponse
