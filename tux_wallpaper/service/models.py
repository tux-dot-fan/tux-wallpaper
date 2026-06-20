"""Pydantic models for Tux Wallpaper service layer.

Defines all data models used across the service layer, API, and player.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class WallpaperSource(str, Enum):
    """Source of a wallpaper."""

    LOCAL = "local"
    REMOTE = "remote"
    BUILTIN = "builtin"


class WallpaperStatus(str, Enum):
    """Download/processing status."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    READY = "ready"
    ERROR = "error"


class WallpaperFormat(str, Enum):
    """Video format of the wallpaper."""

    MP4 = "mp4"
    WEBM = "webm"
    MKV = "mkv"
    AVI = "avi"
    GIF = "gif"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Wallpaper models
# ---------------------------------------------------------------------------


class WallpaperBase(BaseModel):
    """Base wallpaper attributes."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    source: WallpaperSource = WallpaperSource.LOCAL
    format: WallpaperFormat = WallpaperFormat.UNKNOWN
    tags: list[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None


class WallpaperCreate(WallpaperBase):
    """Schema for creating a wallpaper record."""

    remote_id: Optional[str] = None
    remote_url: Optional[str] = None
    file_path: Optional[Path] = Field(default=None, validation_alias="local_path")


class Wallpaper(WallpaperBase):
    """Full wallpaper model with all fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    remote_id: Optional[str] = None
    remote_url: Optional[str] = None
    file_path: Optional[Path] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None  # seconds
    width: Optional[int] = None
    height: Optional[int] = None
    status: WallpaperStatus = WallpaperStatus.PENDING
    download_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    is_favorite: bool = False
    play_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WallpaperSummary(WallpaperBase):
    """Lightweight wallpaper for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    thumbnail_path: Optional[str] = None
    status: WallpaperStatus = WallpaperStatus.PENDING
    is_favorite: bool = False


class WallpaperUpdate(BaseModel):
    """Fields that can be updated on a wallpaper."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    tags: Optional[list[str]] = None
    is_favorite: Optional[bool] = None
    status: Optional[WallpaperStatus] = None


# ---------------------------------------------------------------------------
# Playback state models
# ---------------------------------------------------------------------------


class PlaybackState(BaseModel):
    """Current playback state."""

    state: str  # stopped, playing, paused, error
    wallpaper_id: Optional[int] = None
    wallpaper_title: Optional[str] = None
    position: float = 0.0  # seconds
    duration: Optional[float] = None


class PlaybackCommand(BaseModel):
    """Command to control playback."""

    action: str = Field(..., pattern="^(play|pause|stop|next|prev)$")


# ---------------------------------------------------------------------------
# Settings / Config models
# ---------------------------------------------------------------------------


class PlayerSettings(BaseModel):
    """Player configuration settings."""

    loop: bool = True
    mute: bool = True
    hwdec: str = "auto"
    pause_when_hidden: bool = False
    speed: float = Field(default=1.0, ge=0.1, le=10.0)


class AppSettings(BaseModel):
    """Application-level settings."""

    remote_base_url: Optional[str] = None
    auto_play_on_startup: bool = False
    start_minimized: bool = False
    player: PlayerSettings = Field(default_factory=PlayerSettings)


# ---------------------------------------------------------------------------
# Remote API models (used when talking to server/)
# ---------------------------------------------------------------------------


class RemoteWallpaper(BaseModel):
    """Wallpaper as returned by remote server."""

    id: str
    title: str
    description: Optional[str] = None
    video_url: HttpUrl
    thumbnail_url: Optional[HttpUrl] = None
    tags: list[str] = Field(default_factory=list)
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    is_premium: bool = False


class RemoteWallpaperList(BaseModel):
    """Paginated list from remote server."""

    items: list[RemoteWallpaper]
    total: int
    page: int
    page_size: int
    has_more: bool


# ---------------------------------------------------------------------------
# Generic response wrappers
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str
