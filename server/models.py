"""Server-side data models.

These are database-backed models used by the remote server.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class UserRole(str, Enum):
    """User roles."""

    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class WallpaperVisibility(str, Enum):
    """Wallpaper visibility."""

    PUBLIC = "public"
    PREMIUM = "premium"
    HIDDEN = "hidden"


class UserBase(BaseModel):
    """Base user attributes."""

    email: str
    username: str


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str


class User(UserBase):
    """Full user model."""

    id: int
    role: UserRole = UserRole.USER
    is_premium: bool = False
    created_at: datetime


class WallpaperBase(BaseModel):
    """Base wallpaper attributes."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tags: list[str] = []
    visibility: WallpaperVisibility = WallpaperVisibility.PUBLIC


class WallpaperCreate(WallpaperBase):
    """Schema for creating a wallpaper."""

    video_url: HttpUrl
    thumbnail_url: HttpUrl | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None


class Wallpaper(WallpaperBase):
    """Full wallpaper model."""

    id: int
    slug: str
    video_url: HttpUrl
    thumbnail_url: HttpUrl | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    play_count: int = 0
    created_at: datetime
    updated_at: datetime


class DownloadRecord(BaseModel):
    """Record of a wallpaper download."""

    id: int
    user_id: int
    wallpaper_id: int
    downloaded_at: datetime
