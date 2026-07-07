"""Tux Wallpaper - Video wallpaper player for Linux."""

__version__ = "0.1.0"

import sys
import importlib

# Lazy-load submodules on first attribute access.
# This avoids importing GTK/VLC at package load time (needed for headless test environments).
_SUBMODULES = (
    "commons", "config", "fade", "utils",
    "player", "player.base_player", "player.handlers", "player.video_player",
)


def __getattr__(name: str):
    if name in _SUBMODULES:
        mod = importlib.import_module(f"tux_wallpaper.{name}")
        globals().setdefault(name, mod)
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
