"""Player module for video wallpaper playback.

Provides the high-level WallpaperEngine and individual components:
- WallpaperWindow: GTK3/X11 full-screen borderless window
- MpvPlayer: mpv process controller
- WallpaperEngine: combines window + player
"""

from tux_wallpaper.player.mpv_player import (
    MpvPlayer,
    PlaybackState,
    PlayerConfig,
)
from tux_wallpaper.player.wallpaper_engine import WallpaperEngine
from tux_wallpaper.player.window import (
    WallpaperWindow,
    WindowBackend,
    WindowConfig,
)

__all__ = [
    "MpvPlayer",
    "PlaybackState",
    "PlayerConfig",
    "WallpaperWindow",
    "WallpaperEngine",
    "WindowBackend",
    "WindowConfig",
]
