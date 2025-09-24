"""API dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError
from app.services.user import UserService
from app.services.oauth import GoogleOAuthProvider
from app.models.user import User

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Get current authenticated user supporting both local JWT and Google ID tokens."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_service = UserService(db)
        
        # First try to verify as local JWT token
        user_id_str = verify_token(token)
        if user_id_str is not None:
            # Local JWT token - get user by ID
            try:
                user_id = int(user_id_str)
                user = await user_service.get_user(user_id)
                if user and user.is_active:
                    return user
            except (ValueError, Exception):
                pass  # Fall through to try Google token
        
        # Try to verify as Google ID token
        try:
            oauth_service = GoogleOAuthProvider()
            id_info = await oauth_service.validate_id_token(token)
            
            # Extract Google user ID
            google_user_id = id_info.get("sub")
            if google_user_id:
                user = await user_service.authenticate_oauth_user("google", google_user_id)
                if user and user.is_active:
                    return user
        except Exception:
            pass  # Not a valid Google token
        
        # If we get here, token validation failed
        raise credentials_exception
        
    except AuthenticationError:
        raise credentials_exception
    except Exception:
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    return current_user


async def get_user_service(
    session: AsyncSession = Depends(get_async_db),
) -> UserService:
    """Get UserService instance with database session."""
    return UserService(session)
