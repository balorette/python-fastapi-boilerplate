"""API dependencies."""

from collections.abc import AsyncGenerator, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import SystemPermission, SystemRole
from app.core.database import get_async_db, get_async_db_context
from app.core.exceptions import AuthenticationError
from app.core.security import verify_token
from app.models.user import User
from app.services.oauth import OAuthProviderFactory
from app.services.user import UserService

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
        payload = verify_token(token)
        if payload is not None:
            # Local JWT token - get user by ID from payload
            try:
                user_id_str = payload.get("sub")
                if user_id_str:
                    user_id = int(user_id_str)
                    user = await user_service.get_user(user_id)
                    if user and user.is_active:
                        return user
            except (ValueError, Exception):
                pass  # Fall through to try Google token

        # Try to verify as Google ID token
        try:
            oauth_service = OAuthProviderFactory.create_provider("google")
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


def require_roles(*roles: SystemRole | str) -> Callable[[User], User]:
    """Dependency factory enforcing that the current user has one of the roles."""

    if not roles:
        raise ValueError("At least one role must be specified")

    normalized_roles = {
        role.value if isinstance(role, SystemRole) else str(role).lower()
        for role in roles
    }

    async def _role_guard(current_user: User = Depends(get_current_active_user)) -> User:
        if not any(role in normalized_roles for role in current_user.role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role privileges",
            )
        return current_user

    return _role_guard


def require_permissions(*permissions: SystemPermission | str) -> Callable[[User], User]:
    """Dependency factory enforcing that the current user has all permissions."""

    if not permissions:
        raise ValueError("At least one permission must be specified")

    normalized_permissions = {
        perm.value if isinstance(perm, SystemPermission) else str(perm).lower()
        for perm in permissions
    }

    async def _permission_guard(current_user: User = Depends(get_current_active_user)) -> User:
        missing = normalized_permissions - set(current_user.permission_names)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _permission_guard


async def get_user_service(
    session: AsyncSession = Depends(get_async_db),
) -> UserService:
    """Get UserService instance with database session."""
    return UserService(session)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session for request-scoped dependencies."""

    async with get_async_db_context() as session:
        yield session
