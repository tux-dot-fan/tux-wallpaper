"""User management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from tux_wallpaper.server.core.security import decode_access_token

router = APIRouter()
security = HTTPBearer()


class UserProfile(BaseModel):
    """User profile information."""

    id: int
    email: EmailStr
    username: str
    is_premium: bool = False


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Dependency to get the current authenticated user's ID."""
    token = credentials.credentials
    data = decode_access_token(token)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return data.user_id


@router.get("/me", response_model=UserProfile)
async def get_my_profile(user_id: int = Depends(get_current_user_id)) -> UserProfile:
    """Get the current user's profile."""
    # TODO: Query real database
    return UserProfile(
        id=user_id,
        email="user@example.com",
        username="exampleuser",
        is_premium=False,
    )


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(
    username: str = Field(..., min_length=2, max_length=50),
    user_id: int = Depends(get_current_user_id),
) -> UserProfile:
    """Update the current user's profile."""
    # TODO: Update real database
    return UserProfile(
        id=user_id,
        email="user@example.com",
        username=username,
        is_premium=False,
    )
