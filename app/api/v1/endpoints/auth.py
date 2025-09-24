"""Authentication endpoints."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.security import create_access_token
from app.core.exceptions import AuthenticationError, ValidationError
from app.services.user import UserService
from app.services.oauth import GoogleOAuthProvider
from app.schemas.user import Token, UserResponse
from app.schemas.oauth import GoogleAuthURL, OAuthLoginRequest, OAuthLoginResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_async_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """Login endpoint to get access token."""
    try:
        # Initialize user service
        user_service = UserService(db)
        
        # Authenticate user
        user = await user_service.authenticate_user(
            username=form_data.username,
            password=form_data.password
        )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout")
async def logout():
    """Logout endpoint (for completeness - tokens are stateless)."""
    return {"message": "Successfully logged out"}


@router.get("/oauth/google/authorize", response_model=GoogleAuthURL)
async def google_authorize(request: Request) -> Any:
    """Get Google OAuth authorization URL."""
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not enabled"
        )
    
    oauth_service = GoogleOAuthProvider()
    
    if not oauth_service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not properly configured"
        )
    
    # Generate authorization URL with CSRF protection
    auth_url, state = oauth_service.generate_auth_url()
    
    # Store state in session for CSRF protection (in production, use Redis or secure session storage)
    request.session["oauth_state"] = state
    
    return GoogleAuthURL(url=auth_url, state=state)


@router.post("/oauth/google/callback", response_model=OAuthLoginResponse)
async def google_callback(
    oauth_request: OAuthLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """Handle Google OAuth callback and create/login user."""
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not enabled"
        )
    
    oauth_service = GoogleOAuthService()
    user_service = UserService(db)
    
    try:
        # Verify CSRF state (in production, verify against stored state)
        if oauth_request.state:
            stored_state = request.session.get("oauth_state")
            if not stored_state or stored_state != oauth_request.state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid state parameter"
                )
        
        # Exchange authorization code for tokens
        token_response = await oauth_service.exchange_code_for_tokens(oauth_request.code)
        
        # Get user information from Google
        google_user_info = await oauth_service.get_user_info(token_response.access_token)
        
        # Create or update user in our database
        user, is_new_user = await user_service.create_or_update_oauth_user(
            google_user_info, 
            token_response.refresh_token
        )
        
        # Create our JWT access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        # Clean up session state
        request.session.pop("oauth_state", None)
        
        return OAuthLoginResponse(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "oauth_provider": user.oauth_provider
            },
            is_new_user=is_new_user
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth authentication failed: {str(e)}"
        )
