"""User management endpoints."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> Any:
    """Get list of users."""
    # In a real application, you would fetch users from database
    # For demo purposes, returning mock data
    return [
        {
            "id": 1,
            "email": "admin@example.com",
            "username": "admin",
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
    ]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Create a new user."""
    # In a real application, you would:
    # 1. Check if user already exists
    # 2. Hash password
    # 3. Create user in database
    # 4. Return created user
    
    # For demo purposes, returning mock response
    return {
        "id": 2,
        "email": user.email,
        "username": user.username,
        "is_active": user.is_active,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
) -> Any:
    """Get user by ID."""
    if user_id == 1:
        return {
            "id": 1,
            "email": "admin@example.com",
            "username": "admin",
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
) -> Any:
    """Update user by ID."""
    # In a real application, you would:
    # 1. Fetch user from database
    # 2. Update user fields
    # 3. Save to database
    # 4. Return updated user
    
    if user_id != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": 1,
        "email": user_update.email or "admin@example.com",
        "username": user_update.username or "admin",
        "is_active": user_update.is_active if user_update.is_active is not None else True,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    }


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
) -> None:
    """Delete user by ID."""
    if user_id != 1:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # In a real application, you would delete the user from database
    return