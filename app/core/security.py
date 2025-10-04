"""OAuth2-compliant security utilities for authentication and authorization."""

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    expires_delta_minutes: int | None = None,
) -> str:
    """Create OAuth2-compliant JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    elif expires_delta_minutes:
        expire = datetime.now(UTC) + timedelta(minutes=expires_delta_minutes)
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # OAuth2/OIDC standard claims
    to_encode.update(
        {
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "nbf": int(datetime.now(UTC).timestamp()),
            "iss": settings.JWT_ISSUER,  # Token issuer
            "aud": settings.JWT_AUDIENCE,  # Token audience
            "token_type": "access_token",
        }
    )

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(user_id: int | str) -> str:
    """Create refresh token for token renewal."""
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "token_type": "refresh_token",
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge for secure OAuth2 flow."""
    # Generate cryptographically random code verifier
    code_verifier = (
        base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
    )

    # Create code challenge using SHA256
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )

    return code_verifier, code_challenge


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code verifier against challenge."""
    expected_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )

    return expected_challenge == code_challenge


def verify_token(token: str, token_type: str = "access_token") -> dict[str, Any] | None:
    """Verify JWT token and return payload with type checking."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )

        # Verify token type
        if payload.get("token_type") != token_type:
            return None

        return payload

    except JWTError:
        return None


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode JWT token and return full payload."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        return payload
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token(email: str) -> str:
    """Generate password reset token."""
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expires = now + delta

    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    """Verify password reset token and return email."""
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Check token type
        if decoded_token.get("type") != "reset":
            return None

        return decoded_token["sub"]
    except JWTError:
        return None
