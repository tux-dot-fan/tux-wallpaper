"""mpv-based wallpaper player engine.

Controls mpv process for playing video wallpapers on Wayland/X11.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """Player playback state."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class PlayerConfig:
    """Configuration for mpv player."""

    loop: bool = True
    mute: bool = True
    pause_when_hidden: bool = False
    hwdec: str = "auto"  # hardware decoding
    vo: str = "wayland,x11,null"  # video output
    audio_client: str = "none"  # don't open audio device
    speed: float = 1.0
    volume: int = 0  # 0 for muted


@dataclass
class MpvPlayer:
    """Controls an mpv process for wallpaper playback.

    Uses mpv as a backend renderer. On Wayland, renders to a layer-shell
    window. On X11, renders to a desktop-type X11 window.

    The player is controlled via IPC commands sent through mpv's
    socket-based JSON command interface.
    """

    config: PlayerConfig = field(default_factory=PlayerConfig)
    _process: Optional[subprocess.Popen] = field(
        default=None, repr=False
    )
    _window_id: Optional[int] = field(default=None, repr=False)
    _state: PlaybackState = field(default=PlaybackState.STOPPED)
    _current_file: Optional[Path] = field(default=None, repr=False)
    _state_callbacks: list[Callable[[PlaybackState], None]] = field(
        default_factory=list, repr=False
    )

    def __post_init__(self) -> None:
        self._log = logger

    def set_state_callback(
        self, callback: Callable[[PlaybackState], None]
    ) -> None:
        """Register a callback for state changes."""
        self._state_callbacks.append(callback)

    def _update_state(self, new_state: PlaybackState) -> None:
        """Update state and notify listeners."""
        if self._state != new_state:
            self._state = new_state
            for cb in self._state_callbacks:
                try:
                    cb(new_state)
                except Exception as exc:
                    self._log.warning(f"State callback error: {exc}")

    def load(self, video_path: Path) -> None:
        """Load a video file for playback.

        Does not start playback. Call play() to begin.

        Args:
            video_path: Path to video file (mp4, webm, mkv, etc.)
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self._log.info(f"Loading video: {video_path}")
        self._current_file = video_path

    def play(self) -> None:
        """Start or resume playback."""
        if self._current_file is None:
            raise RuntimeError("No video loaded. Call load() first.")

        if self._process is not None:
            self._resume()
            return

        self._log.info(f"Starting playback: {self._current_file}")
        self._start_process()
        self._update_state(PlaybackState.PLAYING)

    def _start_process(self) -> None:
        """Start the mpv subprocess."""
        if self._current_file is None:
            raise RuntimeError("No video file set")

        self._stop_process()

        mpv_args = self._build_mpv_args()
        self._log.debug(f"mpv args: {mpv_args}")

        env = os.environ.copy()
        env.update({
            "MPV_LEGACY_MKOVR_OPEN": "no",
            "WAYLAND_DISPLAY": os.environ.get("WAYLAND_DISPLAY", ""),
            "DISPLAY": os.environ.get("DISPLAY", ""),
        })

        try:
            self._process = subprocess.Popen(
                ["mpv", *mpv_args, str(self._current_file)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
            self._update_state(PlaybackState.PLAYING)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "mpv is not installed. Install with: sudo apt install mpv"
            ) from exc

    def _build_mpv_args(self) -> list[str]:
        """Build mpv command-line arguments from config."""
        args = [
            "--no-terminal",
            f"--hwdec={self.config.hwdec}",
            f"--vo={self.config.vo}",
            f"--audio-client={self.config.audio_client}",
            f"--speed={self.config.speed}",
        ]

        if self.config.loop:
            args.append("--loop=inf")

        if self.config.mute:
            args.append("--mute=yes")
            args.append("--volume=0")

        if self._window_id is not None:
            args.append(f"--wid={self._window_id}")

        return args

    def pause(self) -> None:
        """Pause playback."""
        if self._process is None:
            return
        self._send_command("set", "pause", "yes")
        self._update_state(PlaybackState.PAUSED)

    def _resume(self) -> None:
        """Resume paused playback."""
        if self._process is None:
            return
        self._send_command("set", "pause", "no")
        self._update_state(PlaybackState.PLAYING)

    def stop(self) -> None:
        """Stop playback and terminate mpv process."""
        self._log.info("Stopping playback")
        self._stop_process()
        self._current_file = None
        self._update_state(PlaybackState.STOPPED)

    def _stop_process(self) -> None:
        """Terminate the mpv subprocess if running."""
        if self._process is not None:
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                self._process.wait(timeout=3)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            finally:
                self._process = None

    def _send_command(self, *args: str) -> None:
        """Send a JSON command to mpv via IPC."""
        # TODO: Implement proper IPC via socket
        # For now, commands are simplified - actual implementation
        # will use mpv's --input-ipc-server socket
        self._log.debug(f"mpv command: {args}")

    def toggle_pause(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        elif self._state == PlaybackState.PAUSED:
            self._resume()
        elif self._state == PlaybackState.STOPPED and self._current_file:
            self.play()

    @property
    def state(self) -> PlaybackState:
        """Get current playback state."""
        return self._state

    @property
    def current_file(self) -> Optional[Path]:
        """Get currently loaded video file."""
        return self._current_file

    @property
    def is_running(self) -> bool:
        """Check if mpv process is running."""
        return self._process is not None and self._process.poll() is None

    def set_window_id(self, window_id: int) -> None:
        """Set the window ID for mpv to render into."""
        self._window_id = window_id

    def set_speed(self, speed: float) -> None:
        """Set playback speed."""
        self.config.speed = speed
        if self._process:
            self._send_command("set", "speed", str(speed))

    def set_loop(self, loop: bool) -> None:
        """Enable or disable looping."""
        self.config.loop = loop
        if self._process:
            self._send_command(
                "set", "loop", "inf" if loop else "no"
            )

    def close(self) -> None:
        """Stop playback and clean up resources."""
        self.stop()
        self._state_callbacks.clear()
