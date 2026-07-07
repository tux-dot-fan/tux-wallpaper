"""Event handlers for Tux Wallpaper player.

- ActiveHandler: monitors screen lock/unlock via D-Bus
- WindowHandler: monitors window maximize/fullscreen state (X11 only)

Fade class is in tux_wallpaper.fade (no GTK dependencies).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger("TuxWallpaper")


# ---------------------------------------------------------------------------
# Active Handler (screen lock detection)
# ---------------------------------------------------------------------------


class ActiveHandler:
    """Monitor screen lock/unlock via D-Bus session bus.

    Listens to org.gnome.ScreenSaver, org.cinnamon.ScreenSaver, and
    org.freedesktop.ScreenSaver ActiveChanged signals.
    """

    def __init__(self, on_active_changed: Callable[[bool], None]) -> None:
        self._on_active_changed = on_active_changed
        self._proxies: list = []
        self._subscriptions: list = []

        from pydbus import SessionBus

        self._bus = SessionBus()
        screensaver_list = [
            "org.gnome.ScreenSaver",
            "org.cinnamon.ScreenSaver",
            "org.freedesktop.ScreenSaver",
        ]

        for s in screensaver_list:
            try:
                proxy = self._bus.get(s)
                sub = proxy.ActiveChanged.connect(on_active_changed)
                self._proxies.append(proxy)
                self._subscriptions.append((proxy, sub))
                logger.debug(f"ActiveHandler: subscribed to {s}")
            except Exception as e:
                logger.debug(f"ActiveHandler: {s} not available ({e})")

    def cleanup(self) -> None:
        """Cleanup signal subscriptions."""
        self._subscriptions.clear()
        self._proxies.clear()


# ---------------------------------------------------------------------------
# Window Handler (X11 only)
# ---------------------------------------------------------------------------


class WindowHandler:
    """Monitor window maximize/fullscreen state via Wnck (X11 only).

    Not available on Wayland.
    """

    def __init__(self, on_window_state_changed: Callable[[dict[str, bool]], None]) -> None:
        self._on_window_state_changed = on_window_state_changed
        self._signal_handlers: list = []
        self._window_signal_handlers: dict = {}

        from gi.repository import Wnck

        self._screen = Wnck.Screen.get_default()
        self._screen.force_update()

        # Connect screen signals
        for sig in ("window-opened", "window-closed", "active-workspace-changed"):
            hid = getattr(self._screen, f"connect_{sig}")(self._eval)
            self._signal_handlers.append((self._screen, hid))

        # Connect to existing windows
        for win in self._screen.get_windows():
            self._connect_window(win)

        self._prev_state: Optional[dict[str, bool]] = None
        self._eval()  # Initial check

    def _connect_window(self, window) -> None:
        from gi.repository import Wnck

        if window not in self._window_signal_handlers:
            hid = window.connect("state-changed", self._eval)
            self._window_signal_handlers[window] = hid

    def _eval(self, *args) -> None:
        from gi.repository import Wnck

        is_any_maximized = False
        is_any_fullscreen = False

        active_workspace = self._screen.get_active_workspace()
        if active_workspace is None:
            return

        for window in self._screen.get_windows():
            base_state = not Wnck.Window.is_minimized(window) and Wnck.Window.is_on_workspace(
                window, active_workspace
            )
            is_maximized = Wnck.Window.is_maximized(window) and base_state
            is_fullscreen = Wnck.Window.is_fullscreen(window) and base_state

            if is_maximized:
                is_any_maximized = True
            if is_fullscreen:
                is_any_fullscreen = True

        cur_state = {"is_any_maximized": is_any_maximized, "is_any_fullscreen": is_any_fullscreen}

        if self._prev_state is None or self._prev_state != cur_state:
            self._prev_state = cur_state
            logger.debug(f"[WindowHandler] {cur_state}")
            self._on_window_state_changed(cur_state)

    def cleanup(self) -> None:
        """Disconnect all signal handlers."""
        for obj, hid in self._signal_handlers:
            try:
                obj.disconnect(hid)
            except Exception as e:
                logger.warning(f"WindowHandler: disconnect error: {e}")
        self._signal_handlers.clear()

        for window, hid in list(self._window_signal_handlers.items()):
            try:
                window.disconnect(hid)
            except Exception as e:
                logger.warning(f"WindowHandler: window disconnect error: {e}")
        self._window_signal_handlers.clear()

