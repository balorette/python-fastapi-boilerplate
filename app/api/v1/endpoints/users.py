"""Enhanced user management endpoints with pagination and search."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_active_user, get_user_service
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import User
from app.schemas.pagination import PaginatedResponse, PaginationParams
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get current user information."""
    return current_user


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    order_by: str = Query(None, description="Field to order by (prefix with - for desc)"),
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """Get paginated list of users."""
    try:
        pagination_params = PaginationParams(skip=skip, limit=limit, order_by=order_by)
        users = await user_service.get_users_paginated(pagination_params)
        return users
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate, user_service: UserService = Depends(get_user_service)
) -> Any:
    """Create a new user."""
    try:
        created_user = await user_service.create_user(user)
        return UserResponse.model_validate(created_user)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, user_service: UserService = Depends(get_user_service)
) -> Any:
    """Get user by ID."""
    try:
        user = await user_service.get_user(user_id)
        return UserResponse.model_validate(user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """Update user by ID."""
    try:
        updated_user = await user_service.update_user(user_id, user_update)
        return UserResponse.model_validate(updated_user)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, user_service: UserService = Depends(get_user_service)
) -> None:
    """Delete user by ID."""
    try:
        await user_service.delete_user(user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/search/", response_model=PaginatedResponse[UserResponse])
async def search_users(
    query: str = Query(..., min_length=1, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """Search users by username or email."""
    try:
        from app.schemas.pagination import SearchParams
        search_params = SearchParams(query=query, skip=skip, limit=limit, order_by=None)
        users = await user_service.search_users(search_params)
        return users
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/active/", response_model=PaginatedResponse[UserResponse])
async def get_active_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    order_by: str = Query(None, description="Field to order by (prefix with - for desc)"),
    user_service: UserService = Depends(get_user_service),
) -> Any:
    """Get paginated list of active users only."""
    try:
        pagination_params = PaginationParams(skip=skip, limit=limit, order_by=order_by)
        users = await user_service.get_active_users_paginated(pagination_params)
        return users
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
