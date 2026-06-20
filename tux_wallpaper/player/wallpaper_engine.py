"""High-level wallpaper engine combining window management and mpv playback."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from tux_wallpaper.player.mpv_player import (
    MpvPlayer,
    PlaybackState,
    PlayerConfig,
)
from tux_wallpaper.player.window import (
    WallpaperWindow,
    WindowBackend,
    WindowConfig,
)

logger = logging.getLogger(__name__)


@dataclass
class WallpaperEngine:
    """High-level wallpaper player engine.

    Combines WallpaperWindow (GTK3/X11/XWayland) and MpvPlayer to provide
    a simple play/pause/stop interface for video wallpapers.

    Usage::

        engine = WallpaperEngine()
        engine.load(Path("/path/to/video.mp4"))
        engine.play()

        # or with callbacks
        engine.set_state_callback(lambda state: print(f"State: {state}"))
    """

    player_config: PlayerConfig = field(default_factory=PlayerConfig)
    window_config: WindowConfig = field(default_factory=WindowConfig)

    _window: WallpaperWindow = field(
        default_factory=lambda: WallpaperWindow(), repr=False
    )
    _player: MpvPlayer = field(default_factory=MpvPlayer, repr=False)
    _wallpaper_path: Optional[Path] = field(default=None, repr=False)
    _state_callbacks: list[Callable[[PlaybackState], None]] = field(
        default_factory=list, repr=False
    )

    def __post_init__(self) -> None:
        self._player = MpvPlayer(config=self.player_config)
        self._window = WallpaperWindow(config=self.window_config)
        self._player.set_state_callback(self._on_player_state_change)

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    def load(self, video_path: Path) -> None:
        """Load a video file.

        Args:
            video_path: Path to video file (mp4, webm, mkv, etc.)

        Raises:
            FileNotFoundError: If video file does not exist.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"WallpaperEngine: loading {video_path}")
        self._wallpaper_path = video_path
        self._player.load(video_path)

    def play(self) -> None:
        """Start playing the loaded wallpaper.

        Creates the wallpaper window if not already created, then starts mpv.
        """
        if self._wallpaper_path is None:
            raise RuntimeError("No wallpaper loaded. Call load() first.")

        # Create window if needed
        if not self._window.is_created:
            width, height = self._detect_screen_resolution()
            window_id = self._window.create(width, height)
            self._player.set_window_id(window_id)
            logger.info(f"Wallpaper window created, XID={window_id}")

        self._player.play()

    def pause(self) -> None:
        """Pause playback."""
        self._player.pause()

    def stop(self) -> None:
        """Stop playback and close the wallpaper window."""
        self._player.stop()
        self._window.close()
        logger.info("Wallpaper stopped and window closed")

    def toggle_pause(self) -> None:
        """Toggle between play and pause."""
        self._player.toggle_pause()

    def set_loop(self, loop: bool) -> None:
        """Enable or disable looping."""
        self._player.set_loop(loop)

    def set_mute(self, mute: bool) -> None:
        """Mute or unmute audio."""
        self._player.set_mute(mute)

    def set_speed(self, speed: float) -> None:
        """Set playback speed."""
        self._player.set_speed(speed)

    def set_state_callback(
        self, callback: Callable[[PlaybackState], None]
    ) -> None:
        """Register a callback for playback state changes."""
        self._state_callbacks.append(callback)

    def close(self) -> None:
        """Stop playback and clean up all resources."""
        self._player.close()
        self._window.close()
        self._state_callbacks.clear()
        logger.info("WallpaperEngine closed")

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

    @property
    def state(self) -> PlaybackState:
        """Current playback state."""
        return self._player.state

    @property
    def is_playing(self) -> bool:
        """True if currently playing."""
        return self._player.state == PlaybackState.PLAYING

    @property
    def current_file(self) -> Optional[Path]:
        """Currently loaded wallpaper file."""
        return self._wallpaper_path

    # ------------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------------

    def _on_player_state_change(self, state: PlaybackState) -> None:
        """Forward player state changes to engine callbacks."""
        for cb in self._state_callbacks:
            try:
                cb(state)
            except Exception as exc:
                logger.warning(f"State callback error: {exc}")

    def _detect_screen_resolution(self) -> tuple[int, int]:
        """Detect the primary display resolution.

        Tries multiple methods in order:
        1. xrandr (X11/XWayland)
        2. wlr-randr (wlroots Wayland)
        3. GNOME settings (GNOME Shell)
        4. GTK default screen size
        """
        # Method 1: xrandr (works on X11 and XWayland)
        try:
            result = os.popen(
                "xrandr --current 2>/dev/null | grep -E '^Screen' | "
                "grep -oE '[0-9]+x[0-9]+' | head -1"
            ).read().strip()
            if result:
                w, h = result.split("x")
                logger.debug(f"Detected resolution via xrandr: {w}x{h}")
                return int(w), int(h)
        except Exception as exc:
            logger.debug(f"xrandr resolution detection failed: {exc}")

        # Method 2: GTK screen size (works universally once GTK is running)
        try:
            import gi

            gi.require_version("Gtk", "3.0")
            from gi.repository import Gdk

            Gdk.init_check()
            screen = Gdk.Screen.get_default()
            if screen:
                w = screen.width()
                h = screen.height()
                logger.debug(f"Detected resolution via GTK: {w}x{h}")
                return w, h
        except Exception as exc:
            logger.debug(f"GTK resolution detection failed: {exc}")

        # Fallback: common HD resolution
        logger.warning("Could not detect resolution, using 1920x1080")
        return 1920, 1080
