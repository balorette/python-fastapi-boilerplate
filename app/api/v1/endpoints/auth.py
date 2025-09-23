"""Authentication endpoints."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import requests

from app.core.config import settings
from app.core.database import get_async_db
from app.core.security import create_access_token
from app.core.exceptions import AuthenticationError
from app.services.user import UserService
from app.schemas.user import Token

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
