"""Local REST API for Tux Wallpaper.

FastAPI-based HTTP API that the Web UI communicates with.
Handles wallpaper management, playback control, and remote server proxying.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import httpx
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from tux_wallpaper.player.mpv_player import PlaybackState
from tux_wallpaper.player.wallpaper_engine import WallpaperEngine
from tux_wallpaper.service.db import Database
from tux_wallpaper.service.models import (
    AppSettings,
    ErrorResponse,
    PlaybackCommand,
    PlaybackState as PlaybackStateModel,
    PlayerSettings,
    RemoteWallpaper,
    RemoteWallpaperList,
    SuccessResponse,
    Wallpaper,
    WallpaperCreate,
    WallpaperSummary,
    WallpaperUpdate,
    WallpaperSource,
    WallpaperStatus,
)

logger = logging.getLogger(__name__)

# Application instance
app = FastAPI(
    title="Tux Wallpaper API",
    version="0.1.0",
    description="Local API for Tux Wallpaper player",
)

# CORS for local web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:18422", "http://localhost:18422"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (initialized on startup)
_database: Optional[Database] = None
_player: Optional[WallpaperEngine] = None
_remote_base_url: str = "http://localhost:18420"
_http_client: Optional[httpx.AsyncClient] = None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_database() -> Database:
    """Dependency for database access."""
    if _database is None:
        raise RuntimeError("Database not initialized. Call startup event first.")
    return _database


def get_player() -> WallpaperEngine:
    """Dependency for player access."""
    if _player is None:
        raise RuntimeError("Player not initialized. Call startup event first.")
    return _player


async def get_http_client() -> httpx.AsyncClient:
    """Dependency for HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:
    """Initialize application state on startup."""
    global _database, _player, _http_client

    from platformdirs import PlatformDirs

    dirs = PlatformDirs("tux-wallpaper", "tux-wallpaper")
    data_dir = Path(dirs.user_data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    _database = Database(data_dir / "tux-wallpaper.db")
    _player = WallpaperEngine()
    _http_client = httpx.AsyncClient(timeout=30.0)

    logger.info("Tux Wallpaper API started")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Clean up on shutdown."""
    global _http_client
    if _player:
        _player.close()
    if _http_client:
        await _http_client.aclose()
    logger.info("Tux Wallpaper API stopped")


# ---------------------------------------------------------------------------
# Wallpaper endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/wallpapers",
    response_model=list[WallpaperSummary],
    summary="List wallpapers",
)
async def list_wallpapers(
    source: Optional[WallpaperSource] = None,
    status: Optional[WallpaperStatus] = None,
    favorite: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Database = Depends(get_database),
) -> list[WallpaperSummary]:
    """List wallpapers with optional filters."""
    wallpapers = db.list_wallpapers(
        source=source,
        status=status,
        favorite_only=favorite,
        limit=limit,
        offset=offset,
    )
    return [
        WallpaperSummary(
            id=w.id,
            title=w.title,
            description=w.description,
            source=w.source,
            format=w.format,
            tags=w.tags,
            thumbnail_url=w.thumbnail_url,
            thumbnail_path=None,
            status=w.status,
            is_favorite=w.is_favorite,
        )
        for w in wallpapers
    ]


@app.get(
    "/api/wallpapers/{wallpaper_id}",
    response_model=Wallpaper,
    responses={404: {"model": ErrorResponse}},
    summary="Get wallpaper details",
)
async def get_wallpaper(
    wallpaper_id: int,
    db: Database = Depends(get_database),
) -> Wallpaper:
    """Get a single wallpaper by ID."""
    wallpaper = db.get_wallpaper(wallpaper_id)
    if wallpaper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallpaper {wallpaper_id} not found",
        )
    return wallpaper


@app.post(
    "/api/wallpapers",
    response_model=Wallpaper,
    status_code=status.HTTP_201_CREATED,
    summary="Create wallpaper entry",
)
async def create_wallpaper(
    wallpaper: WallpaperCreate,
    db: Database = Depends(get_database),
) -> Wallpaper:
    """Create a new wallpaper entry."""
    try:
        return db.create_wallpaper(wallpaper)
    except Exception as exc:
        logger.error(f"Failed to create wallpaper: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


def _probe_video_metadata(file_path: Path) -> dict:
    """Use ffprobe to get video duration, width, and height."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {}
        data = json.loads(result.stdout)

        # Find video stream
        duration = None
        width = height = None
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        if video_stream:
            width = int(video_stream.get("width", 0) or 0)
            height = int(video_stream.get("height", 0) or 0)
        fmt = data.get("format", {})
        if fmt.get("duration"):
            duration = float(fmt["duration"])
        return {"duration": duration, "width": width, "height": height}
    except Exception:
        return {}


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv"}


@app.post(
    "/api/wallpapers/upload",
    response_model=Wallpaper,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a local video file",
)
async def upload_wallpaper(
    file: UploadFile,
    db: Database = Depends(get_database),
) -> Wallpaper:
    """Upload a local video file and create a wallpaper entry.

    The file is saved to the user's cache directory and ffprobe is used
    to extract video metadata (duration, resolution).
    """
    from platformdirs import PlatformDirs

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format: {ext}. Supported: {', '.join(SUPPORTED_VIDEO_EXTENSIONS)}",
        )

    # Save to cache directory
    dirs = PlatformDirs("tux-wallpaper", "tux-wallpaper")
    cache_dir = Path(dirs.user_cache_dir) / "videos"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Generate safe local filename
    import uuid
    local_name = f"{uuid.uuid4().hex[:8]}{ext}"
    local_path = cache_dir / local_name

    try:
        content = await file.read()
        file_size = len(content)
        with open(local_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {exc}",
        )

    # Probe for metadata
    metadata = _probe_video_metadata(local_path)

    # Detect format from extension
    from tux_wallpaper.service.models import WallpaperFormat
    fmt_map = {
        ".mp4": WallpaperFormat.MP4,
        ".webm": WallpaperFormat.WEBM,
        ".mkv": WallpaperFormat.MKV,
        ".avi": WallpaperFormat.AVI,
        ".mov": WallpaperFormat.MOV,
        ".wmv": WallpaperFormat.WMV,
    }
    wallpaper_format = fmt_map.get(ext, WallpaperFormat.UNKNOWN)

    # Extract title from original filename (strip extension)
    title = Path(file.filename).stem

    # Create wallpaper record
    try:
        wallpaper = db.create_wallpaper(
            WallpaperCreate(
                title=title,
                source=WallpaperSource.LOCAL,
                format=wallpaper_format,
                file_path=local_path,
                file_size=file_size,
                duration=metadata.get("duration"),
                width=metadata.get("width"),
                height=metadata.get("height"),
                tags=[],
                status=WallpaperStatus.READY,
            )
        )
        logger.info(f"Uploaded local wallpaper: {wallpaper.id} -> {local_path}")
        return wallpaper
    except Exception as exc:
        # Clean up file on DB failure
        local_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create wallpaper record: {exc}",
        )


@app.patch(
    "/api/wallpapers/{wallpaper_id}",
    response_model=Wallpaper,
    responses={404: {"model": ErrorResponse}},
    summary="Update wallpaper",
)
async def update_wallpaper(
    wallpaper_id: int,
    update: WallpaperUpdate,
    db: Database = Depends(get_database),
) -> Wallpaper:
    """Update a wallpaper's metadata."""
    wallpaper = db.update_wallpaper(wallpaper_id, update)
    if wallpaper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallpaper {wallpaper_id} not found",
        )
    return wallpaper


@app.delete(
    "/api/wallpapers/{wallpaper_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Delete wallpaper",
)
async def delete_wallpaper(
    wallpaper_id: int,
    db: Database = Depends(get_database),
) -> SuccessResponse:
    """Delete a wallpaper and its local file."""
    wallpaper = db.get_wallpaper(wallpaper_id)
    if wallpaper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallpaper {wallpaper_id} not found",
        )

    # Delete local file if exists
    if wallpaper.file_path and wallpaper.file_path.exists():
        try:
            wallpaper.file_path.unlink()
        except OSError as exc:
            logger.warning(f"Failed to delete file {wallpaper.file_path}: {exc}")

    db.delete_wallpaper(wallpaper_id)
    return SuccessResponse(message=f"Wallpaper {wallpaper_id} deleted")


# ---------------------------------------------------------------------------
# Playback endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/playback/state",
    response_model=PlaybackStateModel,
    summary="Get playback state",
)
async def get_playback_state(
    player: WallpaperEngine = Depends(get_player),
    db: Database = Depends(get_database),
) -> PlaybackStateModel:
    """Get current playback state."""
    wallpaper_id = None
    wallpaper_title = None

    if player.current_file:
        wallpapers = db.list_wallpapers(limit=1000)
        for w in wallpapers:
            if w.file_path == player.current_file:
                wallpaper_id = w.id
                wallpaper_title = w.title
                break

    return PlaybackStateModel(
        state=player.state.value,
        wallpaper_id=wallpaper_id,
        wallpaper_title=wallpaper_title,
        position=0.0,
        duration=None,
    )


@app.post(
    "/api/playback/command",
    response_model=SuccessResponse,
    summary="Send playback command",
)
async def playback_command(
    command: PlaybackCommand,
    player: WallpaperEngine = Depends(get_player),
) -> SuccessResponse:
    """Send a playback command (play, pause, stop)."""
    if command.action == "play":
        if player.current_file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No wallpaper loaded. Call POST /api/playback/wallpaper/{id} first.",
            )
        player.play()
    elif command.action == "pause":
        player.pause()
    elif command.action == "stop":
        player.stop()
    elif command.action == "next":
        # TODO: implement playlist next
        pass
    elif command.action == "prev":
        # TODO: implement playlist prev
        pass

    return SuccessResponse(message=f"Command '{command.action}' sent")


@app.post(
    "/api/playback/wallpaper/{wallpaper_id}",
    response_model=SuccessResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Play a wallpaper",
)
async def play_wallpaper(
    wallpaper_id: int,
    player: WallpaperEngine = Depends(get_player),
    db: Database = Depends(get_database),
) -> SuccessResponse:
    """Load and play a wallpaper video."""
    wallpaper = db.get_wallpaper(wallpaper_id)
    if wallpaper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallpaper {wallpaper_id} not found",
        )

    if wallpaper.status != WallpaperStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Wallpaper {wallpaper_id} is not ready (status: {wallpaper.status.value})",
        )

    if not wallpaper.file_path or not wallpaper.file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallpaper file not found for {wallpaper_id}",
        )

    player.load(wallpaper.file_path)
    player.play()

    return SuccessResponse(message=f"Playing: {wallpaper.title}")


# ---------------------------------------------------------------------------
# Settings endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/settings/player",
    response_model=PlayerSettings,
    summary="Get player settings",
)
async def get_player_settings(
    db: Database = Depends(get_database),
) -> PlayerSettings:
    """Get current player settings."""
    return db.get_player_settings()


@app.put(
    "/api/settings/player",
    response_model=PlayerSettings,
    summary="Update player settings",
)
async def update_player_settings(
    settings: PlayerSettings,
    db: Database = Depends(get_database),
    player: WallpaperEngine = Depends(get_player),
) -> PlayerSettings:
    """Update player settings."""
    db.save_player_settings(settings)

    # Apply to running player
    player.set_loop(settings.loop)
    player.set_mute(settings.mute)
    player.set_speed(settings.speed)

    return settings


# ---------------------------------------------------------------------------
# Remote server proxy
# ---------------------------------------------------------------------------


@app.get(
    "/api/remote/wallpapers",
    response_model=RemoteWallpaperList,
    summary="List remote wallpapers",
)
async def list_remote_wallpapers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: Optional[str] = None,
    tag: Optional[str] = None,
    http: httpx.AsyncClient = Depends(get_http_client),
) -> RemoteWallpaperList:
    """Proxy to remote wallpaper server."""
    params: dict[str, str | int] = {"page": page, "page_size": page_size}
    if q:
        params["q"] = q
    if tag:
        params["tag"] = tag

    try:
        response = await http.get(
            f"{_remote_base_url}/api/wallpapers",
            params=params,
        )
        response.raise_for_status()
        return RemoteWallpaperList(**response.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Remote server error: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to remote server: {exc}",
        )


@app.post(
    "/api/remote/wallpapers/{remote_id}/download",
    response_model=Wallpaper,
    status_code=status.HTTP_201_CREATED,
    summary="Download a remote wallpaper",
)
async def download_remote_wallpaper(
    remote_id: str,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_database),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> Wallpaper:
    """Start downloading a wallpaper from the remote server.

    The actual download happens in the background.
    """
    try:
        response = await http.get(
            f"{_remote_base_url}/api/wallpapers/{remote_id}"
        )
        response.raise_for_status()
        remote: RemoteWallpaper = RemoteWallpaper(**response.json())
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Remote server error: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to remote server: {exc}",
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid remote response: {exc}",
        )

    # Create local wallpaper record
    from tux_wallpaper.service.models import WallpaperFormat

    format_str = remote.video_url.path.split(".")[-1].lower()
    try:
        fmt = WallpaperFormat(format_str)
    except ValueError:
        fmt = WallpaperFormat.UNKNOWN

    wallpaper = db.create_wallpaper(
        WallpaperCreate(
            title=remote.title,
            description=remote.description,
            source=WallpaperSource.REMOTE,
            format=fmt,
            tags=remote.tags,
            thumbnail_url=str(remote.thumbnail_url) if remote.thumbnail_url else None,
            remote_id=remote.id,
            remote_url=str(remote.video_url),
            status=WallpaperStatus.PENDING,
        )
    )

    # Start background download
    background_tasks.add_task(
        _download_wallpaper_file,
        wallpaper.id,
        str(remote.video_url),
    )

    return wallpaper


async def _download_wallpaper_file(
    wallpaper_id: int,
    url: str,
) -> None:
    """Background task to download wallpaper file."""
    from tux_wallpaper.service.models import WallpaperStatus, WallpaperUpdate

    db = _database
    if db is None:
        return

    wallpaper = db.get_wallpaper(wallpaper_id)
    if wallpaper is None:
        return

    from platformdirs import PlatformDirs

    dirs = PlatformDirs("tux-wallpaper", "tux-wallpaper")
    data_dir = Path(dirs.user_data_dir) / "wallpapers"
    data_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(url).suffix or ".mp4"
    local_path = data_dir / f"wallpaper_{wallpaper_id}{ext}"

    try:
        db.update_wallpaper(
            wallpaper_id,
            WallpaperUpdate(status=WallpaperStatus.DOWNLOADING),
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(local_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            progress = downloaded / total
                            db.update_wallpaper(
                                wallpaper_id,
                                WallpaperUpdate(status=WallpaperStatus.DOWNLOADING),
                            )

        db.update_wallpaper(
            wallpaper_id,
            WallpaperUpdate(
                status=WallpaperStatus.READY,
                file_path=local_path,
                file_size=local_path.stat().st_size,
            ),
        )
        logger.info(f"Downloaded wallpaper {wallpaper_id} to {local_path}")

    except Exception as exc:
        logger.error(f"Failed to download wallpaper {wallpaper_id}: {exc}")
        db.update_wallpaper(
            wallpaper_id,
            WallpaperUpdate(status=WallpaperStatus.ERROR),
        )


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@app.get(
    "/api/stats",
    summary="Get statistics",
)
async def get_stats(
    db: Database = Depends(get_database),
) -> dict:
    """Get application statistics."""
    return {
        "total_wallpapers": db.wallpapers_count(),
        "local_wallpapers": db.wallpapers_count(source=WallpaperSource.LOCAL),
        "remote_wallpapers": db.wallpapers_count(source=WallpaperSource.REMOTE),
        "ready_wallpapers": db.wallpapers_count(status=WallpaperStatus.READY),
        "error_wallpapers": db.wallpapers_count(status=WallpaperStatus.ERROR),
    }
