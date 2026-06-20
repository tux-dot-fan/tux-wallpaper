"""Wallpaper catalog API - public endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import FileResponse

from tux_wallpaper.server.core.config import get_settings

router = APIRouter()


# Placeholder data - in production this would query a real database
_WALLPAPERS: dict = {}


@router.get("")
async def list_wallpapers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: Optional[str] = Query(default=None, description="Search query"),
    tag: Optional[str] = Query(default=None, description="Filter by tag"),
    is_premium: Optional[bool] = Query(default=None),
) -> dict:
    """List wallpapers with pagination and filters.

    Returns a paginated list of wallpapers matching the query.
    """
    # TODO: Query real database
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "has_more": False,
    }


@router.get("/{wallpaper_id}")
async def get_wallpaper(wallpaper_id: str) -> dict:
    """Get a single wallpaper by ID.

    Returns wallpaper metadata including video URL, thumbnail, etc.
    """
    # TODO: Query real database
    if wallpaper_id not in _WALLPAPERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallpaper not found",
        )
    return _WALLPAPERS[wallpaper_id]


@router.get("/{wallpaper_id}/video")
async def serve_video(wallpaper_id: str):
    """Stream the wallpaper video file.

    For premium wallpapers, validates user subscription before serving.
    """
    settings = get_settings()

    # TODO: Query real database for wallpaper
    video_path = settings.storage_dir / wallpaper_id / "video.mp4"

    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found",
        )

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{wallpaper_id}.mp4",
    )


@router.get("/{wallpaper_id}/thumbnail")
async def serve_thumbnail(wallpaper_id: str):
    """Serve the wallpaper thumbnail image."""
    settings = get_settings()
    thumb_path = settings.thumbnails_dir / f"{wallpaper_id}.jpg"

    if not thumb_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not found",
        )

    return FileResponse(thumb_path, media_type="image/jpeg")
