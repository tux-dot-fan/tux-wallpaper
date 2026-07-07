"""Video wallpaper player using VLC.

Implements the Tux Wallpaper player using python-vlc for video playback,
with GTK DrawingArea for window embedding (same approach as hidamari).
"""

from __future__ import annotations

import ctypes
import logging
import subprocess
from typing import Optional

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

import vlc
from pydbus import SessionBus

from ..commons import (
    CONFIG_KEY_BLUR_RADIUS,
    CONFIG_KEY_DATA_SOURCE,
    CONFIG_KEY_FADE_DURATION_SEC,
    CONFIG_KEY_FADE_INTERVAL,
    CONFIG_KEY_MODE,
    CONFIG_KEY_MUTE,
    CONFIG_KEY_MUTE_WHEN_MAXIMIZED,
    CONFIG_KEY_PAUSE_WHEN_MAXIMIZED,
    CONFIG_KEY_STATIC_WALLPAPER,
    CONFIG_KEY_VOLUME,
    CONFIG_TEMPLATE,
    DBUS_NAME_PLAYER,
    LOGGER_NAME,
    MODE_VIDEO,
)
from ..config import ConfigUtil
from ..fade import Fade
from ..utils import is_nvidia_proprietary, is_vdpau_ok, is_wayland
from .base_player import APP_ID, BasePlayer
from .handlers import WindowHandler

logger = logging.getLogger(LOGGER_NAME)

# ---------------------------------------------------------------------------
# VLC Widget (GTK DrawingArea that embeds VLC)
# ---------------------------------------------------------------------------


class VLCWidget(Gtk.DrawingArea):
    """GTK DrawingArea that hosts a VLC media player instance.

    Uses set_xwindow() to embed VLC's X11 window into our GTK widget,
    same technique as hidamari's VLCWidget.
    """

    __gtype_name__ = "VLCWidget"

    def __init__(self, width: int, height: int):
        Gtk.DrawingArea.__init__(self)

        # VLC options: allow screensaver
        vlc_options = ["--no-disable-screensaver"]
        self._instance = vlc.Instance(vlc_options)
        self._player = self._instance.media_player_new()

        def handle_embed(*args):
            self._player.set_xwindow(self.get_window().get_xid())
            return True

        self.connect("realize", handle_embed)
        self.set_size_request(width, height)

    def cleanup(self) -> None:
        """Release VLC resources."""
        try:
            if self._player:
                self._player.stop()
                self._player.release()
                self._player = None
            if self._instance:
                self._instance.release()
                self._instance = None
        except Exception as e:
            logger.warning(f"[VLCWidget] cleanup error: {e}")


# ---------------------------------------------------------------------------
# Player Window (GTK ApplicationWindow with VLCWidget)
# ---------------------------------------------------------------------------


class PlayerWindow(Gtk.ApplicationWindow):
    """Fullscreen wallpaper window with VLC playback.

    One per monitor. Handles play/pause/volume with fade support.
    """

    __gtype_name__ = "PlayerWindow"

    def __init__(self, name: str, width: int, height: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = width
        self.height = height
        self.name = name

        self._vlc_widget = VLCWidget(width, height)
        self.add(self._vlc_widget)
        self._vlc_widget.show()

        # Disable mouse/keyboard input passthrough to VLC
        self._vlc_widget._player.video_set_mouse_input(False)
        self._vlc_widget._player.video_set_key_input(False)

        # Fade timer
        self.fade = Fade()

        self.menu: Optional[Gtk.Menu] = None
        self.connect("button-press-event", self._on_button_press_event)

    def play(self) -> None:
        self._vlc_widget._player.play()

    def play_fade(self, target: int, fade_duration_sec: float, fade_interval: float) -> None:
        self.play()
        cur = 0
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(
            cur=cur,
            target=target,
            step=step,
            fade_interval=fade_interval,
            update_callback=self.set_volume,
        )

    def is_playing(self) -> bool:
        return bool(self._vlc_widget._player.is_playing())

    def pause(self) -> None:
        if self.is_playing():
            self._vlc_widget._player.pause()

    def pause_fade(
        self, fade_duration_sec: float, fade_interval: float, complete_callback=None
    ) -> None:
        cur = self.get_volume()
        target = 0
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(
            cur=cur,
            target=target,
            step=step,
            fade_interval=fade_interval,
            update_callback=self.set_volume,
            complete_callback=complete_callback or self.pause,
        )

    def volume_fade(
        self, target: int, fade_duration_sec: float, fade_interval: float
    ) -> None:
        cur = self.get_volume()
        step = (target - cur) / (fade_duration_sec / fade_interval)
        self.fade.cancel()
        self.fade.start(
            cur=cur,
            target=target,
            step=step,
            fade_interval=fade_interval,
            update_callback=self.set_volume,
        )

    def media_new(self, *args):
        return self._vlc_widget._instance.media_new(*args)

    def set_media(self, *args) -> None:
        self._vlc_widget._player.set_media(*args)

    def set_volume(self, *args) -> None:
        self._vlc_widget._player.audio_set_volume(*args)

    def get_volume(self) -> int:
        return self._vlc_widget._player.audio_get_volume()

    def set_mute(self, is_mute: bool) -> None:
        self._vlc_widget._player.audio_set_mute(is_mute)

    def get_mute(self) -> bool:
        return bool(self._vlc_widget._player.audio_get_mute())

    def get_position(self) -> float:
        return self._vlc_widget._player.get_position()

    def set_position(self, *args) -> None:
        self._vlc_widget._player.set_position(*args)

    def snapshot(self, *args):
        return self._vlc_widget._player.video_take_snapshot(*args)

    def centercrop(self, video_width: Optional[int] = None, video_height: Optional[int] = None) -> None:
        """Crop video to fill screen (center-crop)."""
        if (video_width, video_height) == (None, None):
            w, h = self._vlc_widget._player.video_get_size()
            if w == 0 or h == 0:
                logger.warning("[CenterCrop] video_get_size not ready")
                return
            video_width, video_height = w, h

        window_ratio = self.width / self.height
        video_ratio = video_width / video_height

        if window_ratio == video_ratio:
            return
        elif video_ratio < window_ratio:
            # Window is wider than video
            crop_height = video_width / window_ratio
            top_offset = (video_height - crop_height) / 2
            crop_geometry = f"{int(video_width)}x{int(crop_height + top_offset)}+0+{int(top_offset)}"
        else:
            # Video is wider than window
            crop_width = video_height * window_ratio
            left_offset = (video_width - crop_width) / 2
            crop_geometry = f"{int(crop_width + left_offset)}x{int(video_height)}+{int(left_offset)}+0"

        logger.debug(f"[CenterCrop] geometry: {crop_geometry}")
        self._vlc_widget._player.video_set_crop_geometry(crop_geometry)

    def add_audio_track(self, audio_path: str) -> None:
        self._vlc_widget._player.add_slave(
            vlc.MediaSlaveType(1), audio_path, True
        )

    def _on_button_press_event(self, widget, event) -> bool:
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            # Right-click menu - placeholder
            return True
        return False

    def get_name(self) -> str:
        return self.name

    def cleanup(self) -> None:
        """Release resources."""
        self.fade.cancel()
        if self._vlc_widget:
            self._vlc_widget.cleanup()


# ---------------------------------------------------------------------------
# Video Player (main D-Bus service)
# ---------------------------------------------------------------------------


class VideoPlayer(Gtk.Application, BasePlayer):
    """D-Bus exposed video wallpaper player using VLC.

    Inherits from both Gtk.Application (for GTK lifecycle + window management)
    and BasePlayer (for the D-Bus interface).

    <node>
    <interface name='io.github.tux_wallpaper.player'>
        <property name="mode" type="s" access="read"/>
        <property name="data_source" type="s" access="readwrite"/>
        <property name="volume" type="i" access="readwrite"/>
        <property name="is_mute" type="b" access="readwrite"/>
        <property name="is_playing" type="b" access="read"/>
        <property name="is_paused_by_user" type="b" access="readwrite"/>
        <method name="reload_config"/>
        <method name="pause_playback"/>
        <method name="start_playback"/>
        <method name="quit_player"/>
    </interface>
    </node>
    """

    __gtype_name__ = "VideoPlayer"

    def __init__(self) -> None:
        from gi.repository import Gio

        # Init both parents in proper MRO order:
        # Gtk.Application.__init__ first (sets up the application)
        Gtk.Application.__init__(
            self,
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        # BasePlayer.__init__ second (sets up windows and D-Bus)
        BasePlayer.__init__(self)

        # Initialize X11 threads for hardware decoding
        if is_wayland() and is_nvidia_proprietary() and not is_vdpau_ok():
            logger.warning(
                "Proprietary NVIDIA driver detected. HW acceleration in Wayland may not work."
            )

        x11 = None
        for lib in ["libX11.so", "libX11.so.6"]:
            try:
                x11 = ctypes.cdll.LoadLibrary(lib)
            except OSError:
                pass
            if x11 is not None:
                x11.XInitThreads()
                break

        self.config = ConfigUtil()
        self.reload_config()

        # Static wallpaper (GNOME only)
        self.original_wallpaper_uri: Optional[str] = None
        self.original_wallpaper_uri_dark: Optional[str] = None
        if self._is_gnome():
            try:
                from gi.repository import Gio

                gso = Gio.Settings.new("org.gnome.desktop.background")
                self.original_wallpaper_uri = gso.get_string("picture-uri")
                self.original_wallpaper_uri_dark = gso.get_string("picture-uri-dark")
            except Exception as e:
                logger.debug(f"Could not read GNOME wallpaper settings: {e}")

        # State tracking
        self._is_paused_by_user = False
        self.active_handler: Optional[object] = None
        self.window_handler: Optional[WindowHandler] = None
        self.is_any_maximized = False
        self.is_any_fullscreen = False

    def _is_gnome(self) -> bool:
        import os

        return "gnome" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    # -------------------------------------------------------------------------
    # BasePlayer overrides
    # -------------------------------------------------------------------------

    def new_window(self, gdk_monitor: Gdk.Monitor):
        rect = gdk_monitor.get_geometry()
        name = gdk_monitor.get_model() or f"Monitor-{rect.x},{rect.y}"
        return PlayerWindow(name, rect.width, rect.height, application=self)

    def do_activate(self, *args) -> None:
        super().do_activate(*args)
        self.data_source = self.config.get(CONFIG_KEY_DATA_SOURCE, {})

    def _on_active_changed(self, active: bool) -> None:
        """Handle screen lock/unlock."""
        if active:
            self.pause_playback()
        else:
            if self._should_playback_start():
                self.start_playback()
            else:
                self.pause_playback()

    def _on_window_state_changed(self, state: dict[str, bool]) -> None:
        """Handle window maximize/fullscreen changes."""
        self.is_any_maximized = state["is_any_maximized"]
        self.is_any_fullscreen = state["is_any_fullscreen"]
        logger.info(
            f"is_any_maximized={self.is_any_maximized}, "
            f"is_any_fullscreen={self.is_any_fullscreen}"
        )

        if self.config.get(CONFIG_KEY_PAUSE_WHEN_MAXIMIZED):
            if self._should_playback_start():
                self.start_playback()
            else:
                self.pause_playback()
        elif self.config.get(CONFIG_KEY_MUTE_WHEN_MAXIMIZED):
            for monitor, window in self.windows.items():
                if not monitor.is_primary():
                    continue
                if self.is_any_fullscreen or self.is_any_maximized:
                    window.volume_fade(
                        target=0,
                        fade_duration_sec=self.config.get(CONFIG_KEY_FADE_DURATION_SEC),
                        fade_interval=self.config.get(CONFIG_KEY_FADE_INTERVAL),
                    )
                else:
                    window.volume_fade(
                        target=self.volume,
                        fade_duration_sec=self.config.get(CONFIG_KEY_FADE_DURATION_SEC),
                        fade_interval=self.config.get(CONFIG_KEY_FADE_INTERVAL),
                    )

    def _should_playback_start(self) -> bool:
        if self.config.get(CONFIG_KEY_PAUSE_WHEN_MAXIMIZED) and (
            self.is_any_maximized or self.is_any_fullscreen
        ):
            return False
        if self.is_paused_by_user:
            return False
        return True

    # -------------------------------------------------------------------------
    # D-Bus properties
    # -------------------------------------------------------------------------

    @property
    def mode(self) -> str:
        return self.config.get(CONFIG_KEY_MODE, MODE_VIDEO)

    @property
    def data_source(self) -> str:
        return str(self.config.get(CONFIG_KEY_DATA_SOURCE, {}))

    @data_source.setter
    def data_source(self, data_source) -> None:
        """Load and start playing video sources."""
        if isinstance(data_source, str):
            import json

            try:
                data_source = json.loads(data_source)
            except json.JSONDecodeError:
                # Single path string
                data_source = {"Default": data_source}

        self.config.set(CONFIG_KEY_DATA_SOURCE, data_source)

        if self.mode == MODE_VIDEO:
            self._load_video_sources(data_source)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")

        self.volume = self.config.get(CONFIG_KEY_VOLUME, 50)
        self.is_mute = self.config.get(CONFIG_KEY_MUTE, False)
        self.start_playback()

        # Initialize event handlers
        if not self.active_handler:
            self.active_handler = self._create_active_handler()
        if not self.window_handler and not is_wayland():
            self.window_handler = WindowHandler(self._on_window_state_changed)

        if self.config.get(CONFIG_KEY_STATIC_WALLPAPER) and self.mode == MODE_VIDEO:
            self._set_static_wallpaper()
        else:
            self._restore_original_wallpaper()

    def _load_video_sources(self, data_source: dict) -> None:
        """Load video files into VLC players for each monitor."""
        video_dims: dict = {}

        # Get video dimensions
        for monitor, path in data_source.items():
            if not path:
                path = data_source.get("Default", "")
                if not path:
                    continue
            try:
                dim = subprocess.check_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "v:0",
                        "-show_entries",
                        "stream=width,height",
                        "-of",
                        "csv=s=x:p=0",
                        path,
                    ],
                    encoding="UTF-8",
                ).strip()
                w, h = map(int, dim.split("x"))
                video_dims[monitor] = (w, h)
            except (subprocess.CalledProcessError, ValueError) as e:
                logger.warning(f"Could not probe {path}: {e}")
                video_dims[monitor] = (None, None)

        # Set media on each window
        for monitor, window in self.windows.items():
            model = monitor.get_model()
            if model and model in data_source and data_source[model]:
                source = data_source[model]
            else:
                source = data_source.get("Default", "")
                if not source:
                    continue

            logger.info(f"Setting source {source} on {monitor.get_model()}")
            media = window.media_new(source)
            # Loop: repeat 65535 times (effectively infinite)
            media.add_option("input-repeat=65535")
            # Disable audio on non-primary monitors
            if not monitor.is_primary():
                media.add_option("no-audio")
            window.set_media(media)
            window.set_position(0.0)

            # Apply center-crop
            default_dim = video_dims.get("Default", (None, None))
            monitor_dim = video_dims.get(model, default_dim)
            if monitor_dim[0] is not None:
                window.centercrop(*monitor_dim)

    def _create_active_handler(self):
        """Create ActiveHandler for screen lock detection."""
        return ActiveHandler(self._on_active_changed)

    @property
    def volume(self) -> int:
        return self.config.get(CONFIG_KEY_VOLUME, 50)

    @volume.setter
    def volume(self, value: int) -> None:
        self.config.set(CONFIG_KEY_VOLUME, value)
        for monitor in self.windows:
            if monitor.is_primary():
                self.windows[monitor].set_volume(value)

    @property
    def is_mute(self) -> bool:
        return self.config.get(CONFIG_KEY_MUTE, False)

    @is_mute.setter
    def is_mute(self, value: bool) -> None:
        self.config.set(CONFIG_KEY_MUTE, value)
        for monitor, window in self.windows.items():
            if monitor.is_primary():
                window.set_mute(value)

    @property
    def is_playing(self) -> bool:
        return not self.is_paused_by_user

    @property
    def is_paused_by_user(self) -> bool:
        return self._is_paused_by_user

    @is_paused_by_user.setter
    def is_paused_by_user(self, value: bool) -> None:
        self._is_paused_by_user = value

    # -------------------------------------------------------------------------
    # D-Bus methods
    # -------------------------------------------------------------------------

    def pause_playback(self) -> None:
        for monitor, window in self.windows.items():
            window.pause_fade(
                fade_duration_sec=self.config.get(CONFIG_KEY_FADE_DURATION_SEC),
                fade_interval=self.config.get(CONFIG_KEY_FADE_INTERVAL),
            )

    def start_playback(self) -> None:
        if self._should_playback_start():
            for monitor, window in self.windows.items():
                window.play_fade(
                    target=self.volume,
                    fade_duration_sec=self.config.get(CONFIG_KEY_FADE_DURATION_SEC),
                    fade_interval=self.config.get(CONFIG_KEY_FADE_INTERVAL),
                )

    def reload_config(self) -> None:
        """Reload config from disk."""
        self.config = ConfigUtil()

    def quit_player(self) -> None:
        """Clean up and quit."""
        # Cleanup handlers
        if self.active_handler:
            self.active_handler.cleanup()
        if self.window_handler:
            self.window_handler.cleanup()
        # Cleanup windows
        for monitor, window in self.windows.items():
            if window:
                window.cleanup()
        self.quit()

    # -------------------------------------------------------------------------
    # Static wallpaper (GNOME)
    # -------------------------------------------------------------------------

    def _set_static_wallpaper(self) -> None:
        """Set current video frame as GNOME static wallpaper."""
        if not self.original_wallpaper_uri:
            return
        # TODO: Take VLC snapshot and set via gsettings
        logger.debug("Static wallpaper not yet implemented")

    def _restore_original_wallpaper(self) -> None:
        """Restore original GNOME wallpaper."""
        if not self.original_wallpaper_uri:
            return
        # TODO: Restore original via gsettings
        logger.debug("Restore wallpaper not yet implemented")
