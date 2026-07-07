"""Utility functions for Tux Wallpaper."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Optional

from .commons import (
    AUTOSTART_DESKTOP_CONTENT,
    AUTOSTART_DESKTOP_PATH,
    AUTOSTART_DIR,
    VIDEO_WALLPAPER_DIR,
)

logger = logging.getLogger("TuxWallpaper")


def is_gnome() -> bool:
    """Check if current DE is GNOME."""
    return "gnome" in str(os.environ.get("XDG_CURRENT_DESKTOP", "")).lower()


def is_wayland() -> bool:
    """Check if current session is Wayland."""
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"


def is_x11() -> bool:
    """Check if current session is X11."""
    return os.environ.get("XDG_SESSION_TYPE") == "x11"


def is_nvidia_proprietary() -> bool:
    """Check if GPU is NVIDIA with proprietary driver."""
    try:
        output = subprocess.check_output("glxinfo -B", shell=True, encoding="UTF-8")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return "OpenGL vendor string: NVIDIA Corporation" in output


def is_vdpau_ok() -> bool:
    """Check if VDPAU works."""
    try:
        ret = subprocess.run("vdpauinfo", stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        return False
    return ret.returncode == 0


def is_flatpak() -> bool:
    """Check if running as Flatpak."""
    return os.path.isfile("/.flatpak-info")


def setup_autostart(enable: bool) -> None:
    """Configure autostart desktop entry."""
    os.makedirs(AUTOSTART_DIR, exist_ok=True)
    logger.debug(f"autostart={enable}, path={AUTOSTART_DESKTOP_PATH}")
    if enable:
        with open(AUTOSTART_DESKTOP_PATH, mode="w") as f:
            f.write(AUTOSTART_DESKTOP_CONTENT)
    else:
        if os.path.isfile(AUTOSTART_DESKTOP_PATH):
            os.remove(AUTOSTART_DESKTOP_PATH)


def get_video_paths() -> list[str]:
    """List video files in VIDEO_WALLPAPER_DIR."""
    from gi.repository import Gio
    file_list = []
    if not os.path.isdir(VIDEO_WALLPAPER_DIR):
        return file_list
    for filename in os.listdir(VIDEO_WALLPAPER_DIR):
        filepath = os.path.join(VIDEO_WALLPAPER_DIR, filename)
        file = Gio.File.new_for_path(filepath)
        try:
            info = file.query_info(
                "standard::content-type", Gio.FileQueryInfoFlags.NONE, None
            )
            mime_type = info.get_content_type()
            if "video" in mime_type:
                file_list.append(filepath)
        except Exception:
            pass
    return sorted(file_list)
