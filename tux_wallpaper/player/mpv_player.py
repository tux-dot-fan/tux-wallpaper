"""mpv-based wallpaper player engine.

Controls mpv for playing video wallpapers as a desktop background on
Wayland and X11. Uses python-mpv for process control.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional

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
    hwdec: str = "auto"
    vo: str = "wayland,x11,null"
    speed: float = 1.0
    volume: int = 0
    # When True, skip GTK window creation and delegate to GNOME Shell Extension
    # (for GNOME Wayland where gtk-layer-shell is not supported)
    use_gnome_extension: bool = False


@dataclass
class MpvPlayer:
    """Controls an mpv instance for wallpaper playback.

    mpv is spawned as a subprocess and controlled via the python-mpv
    library which wraps the mpv C API.
    """

    config: PlayerConfig = field(default_factory=PlayerConfig)
    _mpv: Optional["mpv.MPV"] = field(default=None, repr=False)
    _window_id: Optional[int] = field(default=None, repr=False)
    _state: PlaybackState = field(default=PlaybackState.STOPPED)
    _current_file: Optional[Path] = field(default=None, repr=False)
    _state_callbacks: List[Callable[[PlaybackState], None]] = field(
        default_factory=list, repr=False
    )
    _window: Optional[object] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._log = logger

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    def set_state_callback(
        self, callback: Callable[[PlaybackState], None]
    ) -> None:
        """Register a callback for state changes."""
        self._state_callbacks.append(callback)

    def load(self, video_path: Path) -> None:
        """Load a video file for playback."""
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self._log.info(f"Loading video: {video_path}")
        self._current_file = video_path
        self._update_state(PlaybackState.STOPPED)

    def play(self) -> None:
        """Start or resume playback."""
        if self._current_file is None:
            raise RuntimeError("No video loaded. Call load() first.")

        if self._mpv is not None:
            self._mpv.pause = False
            self._update_state(PlaybackState.PLAYING)
            return

        self._log.info(f"Starting playback: {self._current_file}")
        self._start_player()
        self._update_state(PlaybackState.PLAYING)

    def pause(self) -> None:
        """Pause playback."""
        if self._mpv is None:
            return
        self._mpv.pause = True
        self._update_state(PlaybackState.PAUSED)

    def stop(self) -> None:
        """Stop playback and terminate mpv process."""
        self._log.info("Stopping playback")
        self._close_player()
        self._current_file = None
        self._update_state(PlaybackState.STOPPED)

    def toggle_pause(self) -> None:
        """Toggle between play and pause."""
        if self._mpv is None:
            if self._current_file:
                self.play()
            return

        self._mpv.pause = not self._mpv.pause
        self._update_state(
            PlaybackState.PAUSED if self._mpv.pause else PlaybackState.PLAYING
        )

    def set_speed(self, speed: float) -> None:
        """Set playback speed (0.1 to 100)."""
        self.config.speed = speed
        if self._mpv is not None:
            self._mpv.speed = speed

    def set_loop(self, loop: bool) -> None:
        """Enable or disable looping."""
        self.config.loop = loop
        if self._mpv is not None:
            self._mpv.loop = "inf" if loop else "no"

    def set_mute(self, mute: bool) -> None:
        """Mute or unmute audio."""
        self.config.mute = mute
        if self._mpv is not None:
            self._mpv.mute = mute

    def set_window_id(self, window_id: int) -> None:
        """Set the window ID for mpv to render into."""
        self._window_id = window_id
        if self._mpv is not None:
            self._mpv.wid = window_id

    def close(self) -> None:
        """Stop playback and clean up all resources."""
        self._close_player()
        self._state_callbacks.clear()

    # ------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------

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
        return self._mpv is not None

    @property
    def window_id(self) -> Optional[int]:
        """Get the wallpaper window ID."""
        return self._window_id

    # ------------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------------

    def _update_state(self, new_state: PlaybackState) -> None:
        """Update state and notify listeners."""
        if self._state == new_state:
            return
        self._state = new_state
        for cb in self._state_callbacks:
            try:
                cb(new_state)
            except Exception as exc:
                self._log.warning(f"State callback error: {exc}")

    def _build_mpv_options(self) -> List[str]:
        """Build the list of mpv command-line options from config."""
        opts = [
            "--hwdec=%s" % self.config.hwdec,
            "--vo=%s" % self.config.vo,
            "--speed=%.2f" % self.config.speed,
            "--loop=inf" if self.config.loop else "--loop=no",
            "--mute=yes" if self.config.mute else "--mute=no",
            "--volume=%d" % self.config.volume,
            "--force-window=no",
            "--autofit-larger=100%",
            "--keep-open=yes",
        ]
        return opts

    def _start_player(self) -> None:
        """Start the mpv player instance."""
        import mpv  # type: ignore

        if self._mpv is not None:
            self._close_player()

        mpv_args = self._build_mpv_options()

        self._log.debug(f"Starting mpv with args: {mpv_args}")

        try:
            self._mpv = mpv.MPV(
                *mpv_args,
                log_handler=self._mpv_log,
                loglevel="warn",
            )
        except Exception as exc:
            # Fall back to bare mpv if options fail in this build
            self._log.warning(f"mpv with args failed ({exc}), trying bare mpv")
            try:
                self._mpv = mpv.MPV(
                    log_handler=self._mpv_log,
                    loglevel="warn",
                )
            except Exception as exc2:
                raise RuntimeError(
                    f"Failed to start mpv: {exc2}. "
                    "Ensure mpv is installed: sudo apt install mpv"
                ) from exc2

        # Set up property observers
        self._mpv.observe_property("pause", self._on_pause_changed)
        self._mpv.observe_property("eof-reached", self._on_eof)

        if self._current_file:
            self._mpv.play(str(self._current_file))

    def _mpv_log(
        self,
        loglevel: str,
        component: str,
        message: str,
    ) -> None:
        """Handle mpv log messages."""
        if loglevel in ("error", "warn"):
            self._log.warning(f"[mpv/{component}] {message}")

    def _on_pause_changed(self, name: str, paused: bool) -> None:
        """Called when pause state changes via mpv."""
        if paused:
            self._update_state(PlaybackState.PAUSED)
        else:
            self._update_state(PlaybackState.PLAYING)

    def _on_eof(self, name: str, eof: bool) -> None:
        """Called when end of file is reached (for non-looped playback)."""
        if eof and not self.config.loop:
            self._update_state(PlaybackState.STOPPED)

    def _close_player(self) -> None:
        """Terminate the mpv instance."""
        if self._mpv is not None:
            try:
                self._mpv.terminate()
            except Exception as exc:
                self._log.debug(f"mpv termination: {exc}")
            self._mpv = None
            self._update_state(PlaybackState.STOPPED)

        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None
