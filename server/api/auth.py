"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from tux_wallpaper.server.core.security import (
    Token,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter()


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str = Field(..., min_length=2, max_length=50)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user information."""

    id: int
    email: EmailStr
    username: str
    is_premium: bool = False


# Placeholder user store
_USERS_DB: dict[str, dict] = {}


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest) -> Token:
    """Register a new user account.

    Returns a JWT access token.
    """
    if request.email in _USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed = hash_password(request.password)
    user_id = len(_USERS_DB) + 1

    _USERS_DB[request.email] = {
        "id": user_id,
        "email": request.email,
        "username": request.username,
        "password_hash": hashed,
        "is_premium": False,
    }

    access_token = create_access_token(user_id=user_id)
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login(request: LoginRequest) -> Token:
    """Authenticate a user and return a JWT access token.

    The token should be included in the Authorization header for
    subsequent requests: Authorization: Bearer <token>
    """
    user = _USERS_DB.get(request.email)

    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user["id"])
    return Token(access_token=access_token)
