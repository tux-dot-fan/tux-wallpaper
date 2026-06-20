"""Unit tests for the service models."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tux_wallpaper.service.models import (
    PlaybackCommand,
    PlaybackState,
    PlayerSettings,
    Wallpaper,
    WallpaperCreate,
    WallpaperFormat,
    WallpaperSource,
    WallpaperStatus,
    WallpaperSummary,
    WallpaperUpdate,
)


class TestWallpaperFormat:
    """Tests for WallpaperFormat enum."""

    def test_all_formats(self) -> None:
        """Test all format values exist."""
        assert WallpaperFormat.MP4.value == "mp4"
        assert WallpaperFormat.WEBM.value == "webm"
        assert WallpaperFormat.MKV.value == "mkv"
        assert WallpaperFormat.AVI.value == "avi"
        assert WallpaperFormat.GIF.value == "gif"
        assert WallpaperFormat.UNKNOWN.value == "unknown"


class TestWallpaperSource:
    """Tests for WallpaperSource enum."""

    def test_source_values(self) -> None:
        """Test source enum values."""
        assert WallpaperSource.LOCAL.value == "local"
        assert WallpaperSource.REMOTE.value == "remote"
        assert WallpaperSource.BUILTIN.value == "builtin"


class TestWallpaperStatus:
    """Tests for WallpaperStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert WallpaperStatus.PENDING.value == "pending"
        assert WallpaperStatus.DOWNLOADING.value == "downloading"
        assert WallpaperStatus.READY.value == "ready"
        assert WallpaperStatus.ERROR.value == "error"


class TestWallpaperCreate:
    """Tests for WallpaperCreate model."""

    def test_minimal_wallpaper(self) -> None:
        """Test creating with minimal fields."""
        wp = WallpaperCreate(title="Test Video")
        assert wp.title == "Test Video"
        assert wp.source == WallpaperSource.LOCAL
        assert wp.format == WallpaperFormat.UNKNOWN
        assert wp.tags == []
        assert wp.description is None

    def test_full_wallpaper(self) -> None:
        """Test creating with all fields."""
        wp = WallpaperCreate(
            title="My Video",
            description="A test video",
            source=WallpaperSource.REMOTE,
            format=WallpaperFormat.MP4,
            tags=["nature", "4k"],
            remote_id="abc123",
            remote_url="https://example.com/video.mp4",
        )
        assert wp.title == "My Video"
        assert wp.description == "A test video"
        assert wp.source == WallpaperSource.REMOTE
        assert wp.format == WallpaperFormat.MP4
        assert wp.tags == ["nature", "4k"]
        assert wp.remote_id == "abc123"

    def test_title_required(self) -> None:
        """Test title is required."""
        with pytest.raises(ValidationError):
            WallpaperCreate()

    def test_title_min_length(self) -> None:
        """Test title minimum length."""
        with pytest.raises(ValidationError):
            WallpaperCreate(title="")

    def test_title_max_length(self) -> None:
        """Test title maximum length."""
        with pytest.raises(ValidationError):
            WallpaperCreate(title="x" * 256)


class TestWallpaper:
    """Tests for Wallpaper model."""

    def test_wallpaper_creation(self) -> None:
        """Test full wallpaper model."""
        now = datetime.utcnow()
        wp = Wallpaper(
            id=1,
            title="Test",
            source=WallpaperSource.LOCAL,
            format=WallpaperFormat.MP4,
            status=WallpaperStatus.READY,
            created_at=now,
            updated_at=now,
        )
        assert wp.id == 1
        assert wp.title == "Test"
        assert wp.status == WallpaperStatus.READY
        assert wp.is_favorite is False
        assert wp.play_count == 0


class TestWallpaperUpdate:
    """Tests for WallpaperUpdate model."""

    def test_partial_update(self) -> None:
        """Test partial update with only some fields."""
        update = WallpaperUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.description is None
        assert update.is_favorite is None

    def test_favorite_update(self) -> None:
        """Test updating favorite status."""
        update = WallpaperUpdate(is_favorite=True)
        assert update.is_favorite is True


class TestPlayerSettings:
    """Tests for PlayerSettings model."""

    def test_defaults(self) -> None:
        """Test default player settings."""
        settings = PlayerSettings()
        assert settings.loop is True
        assert settings.mute is True
        assert settings.hwdec == "auto"
        assert settings.speed == 1.0

    def test_speed_bounds(self) -> None:
        """Test speed bounds validation."""
        with pytest.raises(ValidationError):
            PlayerSettings(speed=0.0)  # Below minimum

        with pytest.raises(ValidationError):
            PlayerSettings(speed=15.0)  # Above maximum

    def test_valid_speed(self) -> None:
        """Test valid speed values."""
        settings = PlayerSettings(speed=2.0)
        assert settings.speed == 2.0


class TestPlaybackCommand:
    """Tests for PlaybackCommand model."""

    def test_valid_actions(self) -> None:
        """Test all valid playback actions."""
        for action in ["play", "pause", "stop", "next", "prev"]:
            cmd = PlaybackCommand(action=action)
            assert cmd.action == action

    def test_invalid_action(self) -> None:
        """Test invalid action raises error."""
        with pytest.raises(ValidationError):
            PlaybackCommand(action="invalid")
