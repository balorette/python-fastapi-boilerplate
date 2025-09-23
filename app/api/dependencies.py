"""API dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import verify_token
from app.core.exceptions import AuthenticationError
from app.services.user import UserService
from app.models.user import User

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token and get user ID
        user_id_str = verify_token(token)
        if user_id_str is None:
            raise credentials_exception

        # Convert user ID to integer
        try:
            user_id = int(user_id_str)
        except ValueError:
            raise credentials_exception

        # Get user from database
        user_service = UserService(db)
        user = await user_service.get_user(user_id)
        
        if not user:
            raise credentials_exception
            
        return user
        
    except (AuthenticationError, ValueError, Exception):
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
