"""Tux Wallpaper player module.

This package uses lazy imports to avoid GTK/VLC dependencies at import time.
Import the specific classes you need:

    from tux_wallpaper.player.video_player import VideoPlayer
    from tux_wallpaper.player.base_player import BasePlayer
    from tux_wallpaper.player.handlers import ActiveHandler, WindowHandler
    from tux_wallpaper.fade import Fade
"""

from __future__ import annotations
