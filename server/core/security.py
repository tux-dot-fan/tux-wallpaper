"""Security utilities: password hashing and JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import argon2  # type: ignore
import jwt  # type: ignore
from pydantic import BaseModel

from tux_wallpaper.server.core.config import get_settings


class TokenData(BaseModel):
    """JWT token payload."""

    user_id: int
    exp: datetime


class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"


_password_hasher = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using argon2."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        return _password_hasher.verify(hashed, password)
    except argon2.exceptions.VerifyMismatchError:
        return False


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    payload = {
        "user_id": user_id,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT access token."""
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return TokenData(
            user_id=payload["user_id"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(token: str) -> Optional[int]:
    """Dependency to get current user ID from JWT token.

    Use as: async def endpoint(user_id: int = Depends(get_current_user))
    """
    data = decode_access_token(token)
    if data is None:
        return None
    return data.user_id
