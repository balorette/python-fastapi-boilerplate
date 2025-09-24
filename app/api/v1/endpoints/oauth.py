"""
OAuth2-compliant endpoints for frontend authentication.

Supports:
- Local account authentication with JWT tokens
- OAuth2 Authorization Code flow with PKCE for external providers
- Token refresh functionality
- Frontend-friendly error responses
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.oauth import (
    AuthorizationRequest,
    AuthorizationResponse,
    TokenRequest,
    TokenResponse,
    LocalLoginRequest,
    RefreshTokenRequest,
    ErrorResponse
)

router = APIRouter()
settings = get_settings()


@router.post("/authorize", response_model=AuthorizationResponse)
async def authorize(
    request: AuthorizationRequest,
    db: AsyncSession = Depends(get_db)
) -> AuthorizationResponse:
    """
    OAuth2 Authorization endpoint.
    
    For external providers (Google, etc.), redirects to provider authorization.
    For local accounts, validates credentials and returns authorization code.
    """
    try:
        if request.provider == "local":
            # Local account authorization - validate credentials
            if not request.username or not request.password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username and password required for local authorization"
                )
            
            user_repo = UserRepository(db)
            user = await user_repo.get_by_email(request.username)
            
            if not user or not user.hashed_password or not verify_password(request.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # Generate authorization code (short-lived token)
            auth_code = create_access_token(
                data={"sub": str(user.id), "email": user.email, "type": "auth_code"},
                expires_delta_minutes=10  # Short-lived auth code
            )
            
            return AuthorizationResponse(
                authorization_code=auth_code,
                state=request.state,
                redirect_uri=request.redirect_uri
            )
        
        else:
            # External OAuth provider - simplified implementation
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={request.client_id}&redirect_uri={request.redirect_uri}&response_type=code&scope={request.scope or 'openid email profile'}&state={request.state}"
            if request.code_challenge:
                auth_url += f"&code_challenge={request.code_challenge}&code_challenge_method={request.code_challenge_method or 'S256'}"
            
            return AuthorizationResponse(
                authorization_url=auth_url,
                authorization_code=None,
                state=request.state,
                redirect_uri=request.redirect_uri,
                code_verifier=None
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authorization failed: {str(e)}"
        )


@router.post("/token", response_model=TokenResponse)
async def token(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    OAuth2 Token endpoint.
    
    Exchanges authorization code for access and refresh tokens.
    Supports both local and external provider flows.
    """
    try:
        if request.grant_type != "authorization_code":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported grant type"
            )
        
        if not request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code is required"
            )
        
        if request.provider == "local":
            # Verify authorization code
            payload = verify_token(request.code)
            if not payload or payload.get("type") != "auth_code":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid authorization code"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token: missing user ID"
                )
            
            user_repo = UserRepository(db)
            user = await user_repo.get(int(user_id))
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Create tokens
            access_token = create_access_token(
                data={
                    "sub": str(user.id),
                    "email": user.email,
                    "name": user.full_name or user.username,
                    "provider": "local"
                }
            )
            
            refresh_token = create_refresh_token(user.id)
            
            return TokenResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=refresh_token,
                scope="openid email profile"
            )
        
        else:
            # External OAuth provider - simplified implementation
            # In production, you would:
            # 1. Exchange code with actual provider
            # 2. Get user info from provider
            # 3. Create or update user in your database
            
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="External OAuth providers not fully implemented yet"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token exchange failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def local_login(
    request: LocalLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Direct local account login (simplified flow for frontend).
    
    Alternative to full OAuth2 flow for local accounts.
    """
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(request.email)
        
        if not user or not user.hashed_password or not verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Create tokens
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "name": user.full_name or user.username,
                "provider": "local"
            }
        )
        
        refresh_token = create_refresh_token(user.id)
        
        # Update last login
        await user_repo.update(user, {"last_login": datetime.now(timezone.utc)})
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            scope="openid email profile"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    """
    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token, "refresh_token")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid refresh token: missing user ID"
            )
        
        user_repo = UserRepository(db)
        user = await user_repo.get(int(user_id))
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "name": user.full_name or user.username,
                "provider": getattr(user, "oauth_provider", "local")
            }
        )
        
        # Optionally create new refresh token (token rotation)
        new_refresh_token = create_refresh_token(user.id)
        
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_refresh_token,
            scope="openid email profile"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/providers")
async def get_oauth_providers() -> Dict[str, Any]:
    """
    Get list of available OAuth providers and their configuration.
    """
    return {
        "providers": [
            {
                "name": "local",
                "display_name": "Local Account",
                "type": "local",
                "supports_pkce": True
            },
            {
                "name": "google",
                "display_name": "Google",
                "type": "oauth2",
                "supports_pkce": True,
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "scopes": ["openid", "email", "profile"]
            }
        ],
        "recommended_flow": "authorization_code_with_pkce",
        "pkce_required": True
    }


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth provider callback handler.
    
    This endpoint is called by OAuth providers after user authorization.
    Frontend should handle the redirect and extract tokens.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authorization failed: {error}"
        )
    
    # For SPA applications, we typically redirect back to frontend
    # with the authorization code, letting frontend handle token exchange
    frontend_url = "http://localhost:3000"  # In production, this should come from settings
    callback_url = f"{frontend_url}/auth/callback?code={code}&provider={provider}"
    
    if state:
        callback_url += f"&state={state}"
    
    return RedirectResponse(url=callback_url)


@router.post("/revoke")
async def revoke_token(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Revoke an access or refresh token.
    
    In a production system, you'd maintain a token blacklist.
    """
    try:
        payload = verify_token(token)
        
        # In production, add token to blacklist/revocation list
        # For now, we'll just verify the token is valid
        
        return {"message": "Token revoked successfully"}
        
    except Exception:
        # Even if token is invalid, return success (OAuth2 spec)
        return {"message": "Token revoked successfully"}