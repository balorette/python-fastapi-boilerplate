"""API dependencies."""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_async_db
from app.core.security import verify_token
from app.services.user import UserService

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    username = verify_token(token)
    if username is None:
        raise credentials_exception
    
    # In a real application, you would fetch the user from database
    # For demo purposes, returning mock user
    return {"username": username, "id": 1}


def get_current_active_user(
    current_user: dict = Depends(get_current_user)
):
    """Get current active user."""
    # In a real application, you would check if user is active
    return current_user


async def get_user_service(
    session: AsyncSession = Depends(get_async_db)
) -> UserService:
    """Get UserService instance with database session."""
    return UserService(session)