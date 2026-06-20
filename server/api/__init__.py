"""Server API package - public and authenticated endpoints."""

from fastapi import APIRouter

from tux_wallpaper.server.api import wallpapers, auth, users

router = APIRouter()

router.include_router(wallpapers.router, prefix="/wallpapers", tags=["wallpapers"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])

__all__ = ["router"]
