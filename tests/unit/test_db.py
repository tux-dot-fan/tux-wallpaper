"""Unit tests for the database module."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from tux_wallpaper.service.db import Database
from tux_wallpaper.service.models import (
    PlayerSettings,
    WallpaperCreate,
    WallpaperFormat,
    WallpaperSource,
    WallpaperStatus,
    WallpaperUpdate,
)


@pytest.fixture
def db(temp_dir) -> Database:
    """Create an in-memory database for testing."""
    db_path = temp_dir / "test.db"
    return Database(db_path)


class TestDatabase:
    """Tests for Database."""

    def test_schema_initialization(self, db: Database) -> None:
        """Test database creates required tables."""
        with db.connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}

        assert "wallpapers" in tables
        assert "settings" in tables
        assert "playback_history" in tables
        assert "schema_version" in tables

    def test_create_wallpaper(self, db: Database) -> None:
        """Test creating a wallpaper record."""
        wallpaper = db.create_wallpaper(
            WallpaperCreate(
                title="Test Video",
                source=WallpaperSource.LOCAL,
                format=WallpaperFormat.MP4,
            )
        )

        assert wallpaper.id is not None
        assert wallpaper.title == "Test Video"
        assert wallpaper.source == WallpaperSource.LOCAL
        assert wallpaper.format == WallpaperFormat.MP4
        assert wallpaper.status == WallpaperStatus.PENDING

    def test_get_wallpaper(self, db: Database) -> None:
        """Test retrieving a wallpaper by ID."""
        created = db.create_wallpaper(
            WallpaperCreate(title="Test", source=WallpaperSource.LOCAL)
        )

        retrieved = db.get_wallpaper(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Test"

    def test_get_nonexistent_wallpaper(self, db: Database) -> None:
        """Test retrieving a non-existent wallpaper returns None."""
        result = db.get_wallpaper(9999)
        assert result is None

    def test_list_wallpapers(self, db: Database) -> None:
        """Test listing wallpapers."""
        for i in range(5):
            db.create_wallpaper(
                WallpaperCreate(
                    title=f"Video {i}",
                    source=WallpaperSource.LOCAL,
                )
            )

        wallpapers = db.list_wallpapers()
        assert len(wallpapers) == 5

    def test_list_wallpapers_filter_by_source(self, db: Database) -> None:
        """Test filtering wallpapers by source."""
        db.create_wallpaper(
            WallpaperCreate(title="Local", source=WallpaperSource.LOCAL)
        )
        db.create_wallpaper(
            WallpaperCreate(title="Remote", source=WallpaperSource.REMOTE)
        )

        local = db.list_wallpapers(source=WallpaperSource.LOCAL)
        remote = db.list_wallpapers(source=WallpaperSource.REMOTE)

        assert len(local) == 1
        assert len(remote) == 1
        assert local[0].title == "Local"
        assert remote[0].title == "Remote"

    def test_list_wallpapers_filter_by_status(self, db: Database) -> None:
        """Test filtering wallpapers by status."""
        wp1 = db.create_wallpaper(
            WallpaperCreate(title="Ready", source=WallpaperSource.LOCAL)
        )
        db.create_wallpaper(
            WallpaperCreate(title="Pending", source=WallpaperSource.LOCAL)
        )

        db.update_wallpaper(wp1.id, WallpaperUpdate(status=WallpaperStatus.READY))

        ready = db.list_wallpapers(status=WallpaperStatus.READY)
        pending = db.list_wallpapers(status=WallpaperStatus.PENDING)

        assert len(ready) == 1
        assert len(pending) == 1

    def test_update_wallpaper(self, db: Database) -> None:
        """Test updating a wallpaper."""
        wp = db.create_wallpaper(
            WallpaperCreate(title="Original", source=WallpaperSource.LOCAL)
        )

        updated = db.update_wallpaper(
            wp.id,
            WallpaperUpdate(title="Updated", is_favorite=True),
        )

        assert updated is not None
        assert updated.title == "Updated"
        assert updated.is_favorite is True

    def test_delete_wallpaper(self, db: Database) -> None:
        """Test deleting a wallpaper."""
        wp = db.create_wallpaper(
            WallpaperCreate(title="To Delete", source=WallpaperSource.LOCAL)
        )

        assert db.get_wallpaper(wp.id) is not None

        deleted = db.delete_wallpaper(wp.id)
        assert deleted is True
        assert db.get_wallpaper(wp.id) is None

    def test_delete_nonexistent_wallpaper(self, db: Database) -> None:
        """Test deleting a non-existent wallpaper returns False."""
        result = db.delete_wallpaper(9999)
        assert result is False

    def test_favorites_filter(self, db: Database) -> None:
        """Test filtering by favorites."""
        wp1 = db.create_wallpaper(
            WallpaperCreate(title="Favorite", source=WallpaperSource.LOCAL)
        )
        db.create_wallpaper(
            WallpaperCreate(title="Not Favorite", source=WallpaperSource.LOCAL)
        )

        db.update_wallpaper(wp1.id, WallpaperUpdate(is_favorite=True))

        favorites = db.list_wallpapers(favorite_only=True)
        assert len(favorites) == 1
        assert favorites[0].title == "Favorite"

    def test_pagination(self, db: Database) -> None:
        """Test pagination of wallpapers."""
        for i in range(10):
            db.create_wallpaper(
                WallpaperCreate(title=f"Video {i}", source=WallpaperSource.LOCAL)
            )

        first_page = db.list_wallpapers(limit=3, offset=0)
        second_page = db.list_wallpapers(limit=3, offset=3)

        assert len(first_page) == 3
        assert len(second_page) == 3
        assert first_page[0].title == "Video 9"  # Ordered by updated_at DESC
        assert second_page[0].title == "Video 6"


class TestDatabaseSettings:
    """Tests for database settings operations."""

    def test_set_and_get_setting(self, db: Database) -> None:
        """Test setting and getting a value."""
        db.set_setting("test_key", "test_value")
        assert db.get_setting("test_key") == "test_value"

    def test_get_default_setting(self, db: Database) -> None:
        """Test getting a non-existent setting returns default."""
        assert db.get_setting("nonexistent", "default") == "default"

    def test_json_setting(self, db: Database) -> None:
        """Test storing and retrieving JSON-serializable values."""
        data = {"key": "value", "count": 42}
        db.set_setting("json_data", data)
        assert db.get_setting("json_data") == data

    def test_player_settings(self, db: Database) -> None:
        """Test player settings roundtrip."""
        settings = PlayerSettings(loop=False, mute=False, speed=2.0)
        db.save_player_settings(settings)

        retrieved = db.get_player_settings()
        assert retrieved.loop is False
        assert retrieved.mute is False
        assert retrieved.speed == 2.0

    def test_default_player_settings(self, db: Database) -> None:
        """Test default player settings when none saved."""
        settings = db.get_player_settings()
        assert settings.loop is True
        assert settings.mute is True
        assert settings.hwdec == "auto"


class TestDatabaseCounts:
    """Tests for database count operations."""

    def test_wallpapers_count(self, db: Database) -> None:
        """Test total wallpapers count."""
        for i in range(3):
            db.create_wallpaper(
                WallpaperCreate(title=f"Video {i}", source=WallpaperSource.LOCAL)
            )

        assert db.wallpapers_count() == 3

    def test_count_filter_by_source(self, db: Database) -> None:
        """Test counting wallpapers by source."""
        db.create_wallpaper(
            WallpaperCreate(title="Local", source=WallpaperSource.LOCAL)
        )
        db.create_wallpaper(
            WallpaperCreate(title="Remote", source=WallpaperSource.REMOTE)
        )

        assert db.wallpapers_count(source=WallpaperSource.LOCAL) == 1
        assert db.wallpapers_count(source=WallpaperSource.REMOTE) == 1
