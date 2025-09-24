"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, users, oauth

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth2"])
api_router.include_router(users.router, prefix="/users", tags=["users"])