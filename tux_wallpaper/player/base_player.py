"""Base player class for Tux Wallpaper.

BasePlayer is a Gtk.Application that manages wallpaper windows for each monitor.
Subclasses implement specific playback modes (video, stream, webpage).
"""

from __future__ import annotations

import logging
import sys
from abc import abstractmethod
from typing import TYPE_CHECKING, Optional

import setproctitle

from ..commons import DBUS_NAME_PLAYER, LOGGER_NAME

if TYPE_CHECKING:
    from gi.repository import Gtk, Gdk, Gio

logger = logging.getLogger(LOGGER_NAME)

APP_ID = DBUS_NAME_PLAYER


class DummyWindow:
    """Dummy window used before real player is initialized."""

    def __init__(self, *args, **kwargs):
        pass


class BasePlayer:
    """Base wallpaper player with D-Bus interface.

    Manages one window per monitor and exposes a D-Bus interface for
    external control (play/pause/stop/volume/etc.).

    Note: this class does NOT inherit from Gtk.Application directly.
    Subclasses (like VideoPlayer) should inherit from both BasePlayer
    and Gtk.Application to combine the D-Bus interface with GTK lifecycle.
    """

    __gtype_name__ = "BasePlayer"

    #
    # D-Bus introspection interface
    #
    """
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

    def __init__(self) -> None:
        setproctitle.setproctitle("tux-wallpaper")
        self.windows: dict = {}  # monitor -> window
        self._monitor_detect()

    # -------------------------------------------------------------------------
    # Monitor management
    # -------------------------------------------------------------------------

    def _monitor_detect(self) -> None:
        """Detect all monitors and register them."""
        from gi.repository import Gdk

        display = Gdk.Display.get_default()
        if display is None:
            logger.error("No Gdk display available")
            return

        screen = display.get_default_screen()

        for i in range(display.get_n_monitors()):
            monitor = display.get_monitor(i)
            if monitor not in self.windows:
                self.windows[monitor] = None

        screen.connect("size-changed", self._on_size_changed)
        display.connect("monitor-added", self._on_monitor_added)
        display.connect("monitor-removed", self._on_monitor_removed)

    def _on_size_changed(self, *args) -> None:
        """Handle screen size changes (e.g., resolution change)."""
        from gi.repository import Gdk

        logger.info("[Player] size-changed")
        for monitor in self.windows:
            rect = monitor.get_geometry()
            x, y, width, height = rect.x, rect.y, rect.width, rect.height
            if monitor in self.windows and self.windows[monitor] is not None:
                win = self.windows[monitor]
                win.resize(width, height)
                win.move(x, y)

    def _on_monitor_added(self, _: object, gdk_monitor: object, *args) -> None:
        """Handle new monitor hotplug."""
        logger.info("[Player] monitor-added")
        self.windows[gdk_monitor] = None
        self.do_activate()

    def _on_monitor_removed(self, _: object, gdk_monitor: object, *args) -> None:
        """Handle monitor removal."""
        logger.info("[Player] monitor-removed")
        if gdk_monitor in self.windows:
            del self.windows[gdk_monitor]

    # -------------------------------------------------------------------------
    # Window creation (override in subclass)
    # -------------------------------------------------------------------------

    def new_window(self, gdk_monitor: object) -> object:
        """Create a new player window for a monitor. Override in subclass."""
        return DummyWindow(application=self)

    # -------------------------------------------------------------------------
    # Gtk.Application lifecycle (override in subclass that inherits Gtk.Application)
    # -------------------------------------------------------------------------

    def do_startup(self) -> None:
        """GTK startup. Override in Gtk.Application subclass."""
        pass

    def do_activate(self) -> None:
        """Create windows for all monitors and register D-Bus."""
        from gi.repository import Gdk
        from pydbus import SessionBus

        for monitor in self.windows:
            if not self.windows[monitor]:
                window = self.new_window(monitor)
                window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
                rect = monitor.get_geometry()
                x, y, width, height = rect.x, rect.y, rect.width, rect.height
                window.set_size_request(width, height)
                window.move(x, y)
                self.windows[monitor] = window
            self.windows[monitor].present()

        # Publish D-Bus
        bus = SessionBus()
        try:
            bus.publish(DBUS_NAME_PLAYER, self)
            logger.info("D-Bus interface published")
        except RuntimeError as e:
            logger.error(f"D-Bus publish error: {e}")

    # -------------------------------------------------------------------------
    # Abstract properties (override in subclass)
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def mode(self) -> str:
        """Current playback mode."""
        pass

    @property
    @abstractmethod
    def data_source(self) -> str:
        """Current data source path or URL."""
        pass

    @data_source.setter
    @abstractmethod
    def data_source(self, value: str) -> None:
        pass

    @property
    @abstractmethod
    def volume(self) -> int:
        """Current volume (0-100)."""
        pass

    @volume.setter
    @abstractmethod
    def volume(self, value: int) -> None:
        pass

    @property
    @abstractmethod
    def is_mute(self) -> bool:
        """Whether audio is muted."""
        pass

    @is_mute.setter
    @abstractmethod
    def is_mute(self, value: bool) -> None:
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Whether playback is active."""
        pass

    @property
    @abstractmethod
    def is_paused_by_user(self) -> bool:
        """Whether playback is paused by user action."""
        pass

    @is_paused_by_user.setter
    @abstractmethod
    def is_paused_by_user(self, value: bool) -> None:
        pass

    # -------------------------------------------------------------------------
    # Abstract methods (override in subclass)
    # -------------------------------------------------------------------------

    @abstractmethod
    def pause_playback(self) -> None:
        """Pause playback with fade."""
        pass

    @abstractmethod
    def start_playback(self) -> None:
        """Start/resume playback with fade."""
        pass

    @abstractmethod
    def reload_config(self) -> None:
        """Reload configuration from disk."""
        pass

    # -------------------------------------------------------------------------
    # D-Bus methods
    # -------------------------------------------------------------------------

    def quit_player(self) -> None:
        """Quit the player application.

        Subclasses that inherit Gtk.Application should call self.quit() there.
        """
        import sys
        sys.exit(0)
