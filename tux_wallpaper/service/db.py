"""SQLite database for local wallpaper cache and state management."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional

import structlog

from .models import (
    PlaybackState,
    PlayerSettings,
    Wallpaper,
    WallpaperCreate,
    WallpaperSource,
    WallpaperStatus,
    WallpaperUpdate,
)

logger = structlog.get_logger(__name__)

# Schema version for migrations
SCHEMA_VERSION = 1


class Database:
    """SQLite database for Tux Wallpaper local state.

    Manages wallpaper cache, favorites, playback history, and settings.
    Thread-safe using connection per thread.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._connection_pool: dict[int, sqlite3.Connection] = {}
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        import threading

        tid = threading.get_ident()
        if tid not in self._connection_pool:
            conn = sqlite3.connect(
                self._db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._connection_pool[tid] = conn
        return self._connection_pool[tid]

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self.connection() as conn:
            conn.executescript(f"""
                -- Schema version tracking
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                -- Wallpapers table
                CREATE TABLE IF NOT EXISTS wallpapers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    source TEXT NOT NULL DEFAULT 'local',
                    format TEXT NOT NULL DEFAULT 'unknown',
                    tags TEXT NOT NULL DEFAULT '[]',
                    thumbnail_url TEXT,
                    remote_id TEXT,
                    remote_url TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    duration REAL,
                    width INTEGER,
                    height INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    download_progress REAL NOT NULL DEFAULT 0.0,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    play_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Index for common queries
                CREATE INDEX IF NOT EXISTS idx_wallpapers_status
                    ON wallpapers(status);
                CREATE INDEX IF NOT EXISTS idx_wallpapers_source
                    ON wallpapers(source);
                CREATE INDEX IF NOT EXISTS idx_wallpapers_remote_id
                    ON wallpapers(remote_id);

                -- Playback history
                CREATE TABLE IF NOT EXISTS playback_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallpaper_id INTEGER NOT NULL REFERENCES wallpapers(id),
                    played_at TEXT NOT NULL,
                    position REAL NOT NULL DEFAULT 0.0,
                    duration REAL NOT NULL DEFAULT 0.0
                );

                CREATE INDEX IF NOT EXISTS idx_history_wallpaper
                    ON playback_history(wallpaper_id);

                -- App settings (key-value store)
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Initialize schema version
                INSERT OR IGNORE INTO schema_version (version)
                    VALUES ({SCHEMA_VERSION});
            """)

    # -------------------------------------------------------------------------
    # Wallpaper CRUD
    # -------------------------------------------------------------------------

    def create_wallpaper(self, wallpaper: WallpaperCreate) -> Wallpaper:
        """Insert a new wallpaper record."""
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO wallpapers (
                    title, description, source, format, tags,
                    thumbnail_url, remote_id, remote_url, file_path,
                    file_size, duration, width, height, status,
                    download_progress, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    wallpaper.title,
                    wallpaper.description,
                    wallpaper.source.value,
                    wallpaper.format.value,
                    json.dumps(wallpaper.tags),
                    wallpaper.thumbnail_url,
                    wallpaper.remote_id,
                    wallpaper.remote_url,
                    str(wallpaper.file_path) if wallpaper.file_path else None,
                    None,  # file_size
                    None,  # duration
                    None,  # width
                    None,  # height
                    WallpaperStatus.PENDING.value,
                    0.0,
                    now,
                    now,
                ),
            )
            wallpaper_id = cursor.lastrowid
            return self.get_wallpaper(wallpaper_id)

    def get_wallpaper(self, wallpaper_id: int) -> Optional[Wallpaper]:
        """Get a wallpaper by ID."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM wallpapers WHERE id = ?",
                (wallpaper_id,),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_wallpaper(row)

    def list_wallpapers(
        self,
        source: Optional[WallpaperSource] = None,
        status: Optional[WallpaperStatus] = None,
        favorite_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Wallpaper]:
        """List wallpapers with optional filters."""
        query = "SELECT * FROM wallpapers WHERE 1=1"
        params: list[Any] = []

        if source:
            query += " AND source = ?"
            params.append(source.value)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if favorite_only:
            query += " AND is_favorite = 1"

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._row_to_wallpaper(row) for row in rows]

    def update_wallpaper(
        self, wallpaper_id: int, update: WallpaperUpdate
    ) -> Optional[Wallpaper]:
        """Update a wallpaper record."""
        sets: list[str] = []
        params: list[Any] = []

        if update.title is not None:
            sets.append("title = ?")
            params.append(update.title)

        if update.description is not None:
            sets.append("description = ?")
            params.append(update.description)

        if update.tags is not None:
            sets.append("tags = ?")
            params.append(json.dumps(update.tags))

        if update.is_favorite is not None:
            sets.append("is_favorite = ?")
            params.append(1 if update.is_favorite else 0)

        if update.status is not None:
            sets.append("status = ?")
            params.append(update.status.value)

        if not sets:
            return self.get_wallpaper(wallpaper_id)

        sets.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(wallpaper_id)

        with self.connection() as conn:
            conn.execute(
                f"UPDATE wallpapers SET {', '.join(sets)} WHERE id = ?",
                params,
            )

        return self.get_wallpaper(wallpaper_id)

    def delete_wallpaper(self, wallpaper_id: int) -> bool:
        """Delete a wallpaper record."""
        with self.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM wallpapers WHERE id = ?",
                (wallpaper_id,),
            )
            return cursor.rowcount > 0

    def _row_to_wallpaper(self, row: sqlite3.Row) -> Wallpaper:
        """Convert a database row to a Wallpaper model."""
        return Wallpaper(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            source=WallpaperSource(row["source"]),
            format=row["format"],
            tags=json.loads(row["tags"]),
            thumbnail_url=row["thumbnail_url"],
            remote_id=row["remote_id"],
            remote_url=row["remote_url"],
            file_path=Path(row["file_path"]) if row["file_path"] else None,
            file_size=row["file_size"],
            duration=row["duration"],
            width=row["width"],
            height=row["height"],
            status=WallpaperStatus(row["status"]),
            download_progress=row["download_progress"],
            is_favorite=bool(row["is_favorite"]),
            play_count=row["play_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    # -------------------------------------------------------------------------
    # Settings
    # -------------------------------------------------------------------------

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()

        if row is None:
            return default

        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]

    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value."""
        now = datetime.utcnow().isoformat()
        serialized = json.dumps(value) if not isinstance(value, str) else value
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
                """,
                (key, serialized, now, serialized, now),
            )

    def get_player_settings(self) -> PlayerSettings:
        """Get player settings from database."""
        raw = self.get_setting("player", None)
        if raw is None:
            return PlayerSettings()
        return PlayerSettings(**raw) if isinstance(raw, dict) else PlayerSettings()

    def save_player_settings(self, settings: PlayerSettings) -> None:
        """Save player settings to database."""
        self.set_setting("player", settings.model_dump())

    # -------------------------------------------------------------------------
    # Playback history
    # -------------------------------------------------------------------------

    def record_playback(
        self, wallpaper_id: int, position: float, duration: float
    ) -> None:
        """Record a playback event."""
        now = datetime.utcnow().isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO playback_history (wallpaper_id, played_at, position, duration)
                VALUES (?, ?, ?, ?)
                """,
                (wallpaper_id, now, position, duration),
            )
            conn.execute(
                "UPDATE wallpapers SET play_count = play_count + 1, "
                "updated_at = ? WHERE id = ?",
                (now, wallpaper_id),
            )

    def get_recently_played(self, limit: int = 10) -> list[Wallpaper]:
        """Get wallpapers ordered by most recent playback."""
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT w.* FROM wallpapers w
                INNER JOIN playback_history h ON w.id = h.wallpaper_id
                ORDER BY h.played_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_wallpaper(row) for row in rows]

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def wallpapers_count(
        self,
        source: Optional[WallpaperSource] = None,
        status: Optional[WallpaperStatus] = None,
    ) -> int:
        """Get total count of wallpapers."""
        query = "SELECT COUNT(*) FROM wallpapers WHERE 1=1"
        params: list[Any] = []

        if source:
            query += " AND source = ?"
            params.append(source.value)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        with self.connection() as conn:
            return conn.execute(query, params).fetchone()[0]
