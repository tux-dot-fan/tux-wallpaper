"""Constants and shared definitions for Tux Wallpaper."""

from __future__ import annotations

import os
import subprocess

LOGGER_NAME = "TuxWallpaper"

PROJECT = "io.github.tux_wallpaper"
DBUS_NAME_PLAYER = f"{PROJECT}.player"
DBUS_NAME_SERVER = f"{PROJECT}.server"

HOME = os.environ.get("HOME", "/home/dean")

xdg_video_dir = os.environ.get("XDG_VIDEOS_DIR")
if not xdg_video_dir:
    try:
        xdg_video_dir = subprocess.check_output(
            "xdg-user-dir VIDEOS", shell=True, encoding="UTF-8"
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        xdg_video_dir = os.path.join(HOME, "Videos")

VIDEO_WALLPAPER_DIR = os.path.join(xdg_video_dir, "TuxWallpaper")

xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(HOME, ".config"))
CONFIG_DIR = os.path.join(xdg_config_home, "tux-wallpaper")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

AUTOSTART_DIR = os.path.join(xdg_config_home, "autostart")
AUTOSTART_DESKTOP_PATH = os.path.join(AUTOSTART_DIR, f"{PROJECT}.desktop")
AUTOSTART_DESKTOP_CONTENT = """[Desktop Entry]
Name=Tux Wallpaper
Exec=tux-wallpaper -b
Icon=video-desktop
Terminal=false
Type=Application
Categories=GTK;Utility;
StartupNotify=true
"""

# Playback modes
MODE_NULL = "MODE_NULL"
MODE_VIDEO = "MODE_VIDEO"
MODE_STREAM = "MODE_STREAM"
MODE_WEBPAGE = "MODE_WEBPAGE"

# Config version for migrations
CONFIG_VERSION = 4
CONFIG_KEY_VERSION = "version"
CONFIG_KEY_MODE = "mode"
CONFIG_KEY_DATA_SOURCE = "data_source"
CONFIG_KEY_MUTE = "is_mute"
CONFIG_KEY_VOLUME = "audio_volume"
CONFIG_KEY_STATIC_WALLPAPER = "is_static_wallpaper"
CONFIG_KEY_BLUR_RADIUS = "static_wallpaper_blur_radius"
CONFIG_KEY_PAUSE_WHEN_MAXIMIZED = "is_pause_when_maximized"
CONFIG_KEY_MUTE_WHEN_MAXIMIZED = "is_mute_when_maximized"
CONFIG_KEY_FADE_DURATION_SEC = "fade_duration_sec"
CONFIG_KEY_FADE_INTERVAL = "fade_interval"
CONFIG_KEY_SYSTRAY = "is_show_systray"
CONFIG_KEY_FIRST_TIME = "is_first_time"

CONFIG_TEMPLATE = {
    CONFIG_KEY_VERSION: CONFIG_VERSION,
    CONFIG_KEY_MODE: MODE_NULL,
    CONFIG_KEY_DATA_SOURCE: {},
    CONFIG_KEY_MUTE: False,
    CONFIG_KEY_VOLUME: 50,
    CONFIG_KEY_STATIC_WALLPAPER: True,
    CONFIG_KEY_BLUR_RADIUS: 5,
    CONFIG_KEY_PAUSE_WHEN_MAXIMIZED: True,
    CONFIG_KEY_MUTE_WHEN_MAXIMIZED: False,
    CONFIG_KEY_FADE_DURATION_SEC: 1.5,
    CONFIG_KEY_FADE_INTERVAL: 0.1,
    CONFIG_KEY_SYSTRAY: False,
    CONFIG_KEY_FIRST_TIME: True,
}
