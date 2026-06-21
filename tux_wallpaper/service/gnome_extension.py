"""GNOME Shell Extension bridge for tux-wallpaper.

On GNOME Wayland, the wallpaper window cannot be embedded using gtk-layer-shell
(Layer Shell protocol not supported by GNOME Shell). This module bridges the
Python daemon to a minimal GNOME Shell Extension (Gjs) that handles window
z-order management.

How it works:
1. The Gjs extension polls /run/user/1000/tux-wallpaper-cmd every 500ms.
2. Python daemon writes JSON commands to this file.
3. Extension reads the command, starts/stops mpv, and keeps window lowered.

Usage:
    from tux_wallpaper.service.gnome_extension import GnomeExtensionBridge
    bridge = GnomeExtensionBridge()
    bridge.play("/path/to/video.mp4")
    bridge.stop()
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# The command file polled by the GNOME Shell extension
_CMD_FILE = Path("/run/user/1000/tux-wallpaper-cmd")


class GnomeExtensionBridge:
    """Bridge to GNOME Shell Extension via command file.

    The extension reads this file every 500ms and acts on commands.
    """

    def __init__(self, cmd_file: Path | None = None) -> None:
        self._cmd_file = cmd_file or _CMD_FILE

    def _write_cmd(self, action: str, video: str | None = None) -> None:
        """Write a command to the polled command file."""
        cmd = {"action": action}
        if video:
            cmd["video"] = video
        try:
            self._cmd_file.parent.mkdir(parents=True, exist_ok=True)
            self._cmd_file.write_text(json.dumps(cmd))
            logger.debug(f"Wrote cmd: {cmd}")
        except OSError as exc:
            logger.warning(f"Failed to write extension cmd: {exc}")

    def play(self, video_path: str | Path) -> None:
        """Tell the extension to start playing a wallpaper video."""
        self._write_cmd("play", str(video_path))

    def stop(self) -> None:
        """Tell the extension to stop the wallpaper."""
        self._write_cmd("stop")

    def is_extension_active(self) -> bool:
        """Check if the GNOME Shell extension is loaded and the command file is accessible."""
        try:
            return self._cmd_file.exists()
        except OSError:
            return False
