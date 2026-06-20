"""Full-screen wallpaper window management for Wayland and X11.

Uses GTK3 to create a borderless desktop-type window that mpv renders into.
Works on both native X11 and XWayland (GNOME on Wayland).
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WindowBackend(Enum):
    """Window backend / session type."""

    WAYLAND = "wayland"
    X11 = "x11"
    AUTO = "auto"


@dataclass
class WindowConfig:
    """Configuration for wallpaper window."""

    backend: WindowBackend = WindowBackend.AUTO
    fullscreen: bool = True
    layer: str = "background"  # future: wayland compositor hint
    geometry: Optional[str] = None  # e.g., "1920x1080+0+0"


@dataclass
class WallpaperWindow:
    """Creates and manages a full-screen borderless window for wallpaper display.

    On X11 / XWayland: Creates a GTK3 window with _NET_WM_WINDOW_TYPE_DESKTOP
    and embeds mpv into it using --wid.

    On pure Wayland: Uses gtk-layer-shell if available, otherwise falls back
    to a borderless GTK3 window that works under XWayland.
    """

    config: WindowConfig = field(default_factory=WindowConfig)
    _window_id: Optional[int] = field(default=None, repr=False)
    _gtk_window: Optional[object] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._detect_backend()

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    def create(
        self,
        width: int,
        height: int,
        output_name: Optional[str] = None,
    ) -> int:
        """Create a full-screen wallpaper window.

        Args:
            width: Window width in pixels.
            height: Window height in pixels.
            output_name: (Wayland) Specific monitor name; ignored on X11.

        Returns:
            X11 window ID (xid) that mpv uses with --wid.
        """
        logger.info(
            f"Creating wallpaper window {width}x{height} "
            f"(backend={self.config.backend.value})"
        )

        if self.config.backend == WindowBackend.WAYLAND:
            return self._create_wayland_window(width, height, output_name)
        else:
            return self._create_x11_window(width, height)

    def close(self) -> None:
        """Destroy the wallpaper window."""
        if self._gtk_window is not None:
            logger.info(f"Closing wallpaper window {self._window_id}")
            try:
                self._gtk_window.destroy()
            except Exception as exc:
                logger.debug(f"Window destroy: {exc}")
            self._gtk_window = None
            self._window_id = None

    @property
    def window_id(self) -> Optional[int]:
        """Current X11 window ID, or None if not created."""
        return self._window_id

    @property
    def is_created(self) -> bool:
        """True if window is currently created."""
        return self._window_id is not None

    # ------------------------------------------------------------------------
    # Backend detection
    # ------------------------------------------------------------------------

    def _detect_backend(self) -> None:
        """Detect whether we are on Wayland or X11."""
        if self.config.backend != WindowBackend.AUTO:
            return

        wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
        x11_display = os.environ.get("DISPLAY", "")
        session_type = os.environ.get("XDG_SESSION_TYPE", "")

        if session_type == "wayland" or wayland_display:
            # Check if we're running under XWayland (GNOME Shell on Wayland)
            # by seeing if we can actually create X11 windows
            if self._can_create_x11_window():
                self.config.backend = WindowBackend.WAYLAND
                logger.info("Detected XWayland session (GNOME on Wayland)")
            else:
                self.config.backend = WindowBackend.WAYLAND
                logger.info("Detected Wayland session")
        elif x11_display:
            self.config.backend = WindowBackend.X11
            logger.info("Detected X11 session")
        else:
            self.config.backend = WindowBackend.X11
            logger.warning("No session type detected, defaulting to X11")

    def _can_create_x11_window(self) -> bool:
        """Check if we can create X11 windows (works under XWayland too)."""
        try:
            import gi

            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk  # noqa: F401

            Gtk.init_check()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------------
    # Window creation
    # ------------------------------------------------------------------------

    def _create_x11_window(
        self,
        width: int,
        height: int,
    ) -> int:
        """Create a borderless X11 desktop window using GTK3."""
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, GdkX11, GdkPixbuf, Gtk

        # Initialize GTK in subprocess-safe mode
        Gtk.init_check()

        # Create the main window
        window = Gtk.Window()
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_default_size(width, height)
        window.set_position(Gtk.PositionType.CENTER)
        window.stick()
        window.set_keep_below(True)

        # Set up the window as a desktop background
        screen = Gdk.Screen.get_default()
        if screen:
            window.set_screen(screen)

        # Try to set RGBA visual for transparency (optional)
        visual = screen.get_rgba_visual() if screen else None
        if visual:
            window.set_visual(visual)

        # Set window type hint to DESKTOP so window managers treat it as bg
        window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)

        # Realize to get the X11 window ID
        window.realize()
        window.move(0, 0)

        xid = window.get_xid()
        self._window_id = xid
        self._gtk_window = window

        # Apply X11-specific atoms for desktop behavior
        self._set_x11_desktop_atoms(window)

        # Show the window (without activating/focusing)
        window.show()

        logger.info(f"Created X11 wallpaper window, XID={xid}")
        return xid

    def _create_wayland_window(
        self,
        width: int,
        height: int,
        output_name: Optional[str] = None,
    ) -> int:
        """Create a Wayland surface using gtk-layer-shell, or fall back to GTK3.

        gtk-layer-shell is preferred for proper layer-shell support on
        wlroots compositors (Sway, Wayfire, etc.). Falls back to GTK3
        borderless window which works on GNOME Shell via XWayland.
        """
        try:
            import gtk_layer_shell  # type: ignore

            return self._create_layer_shell_window(width, height, output_name)
        except ImportError:
            logger.info(
                "gtk-layer-shell not available, falling back to GTK3 borderless "
                "window (works on XWayland/GNOME)"
            )
            return self._create_x11_window(width, height)

    def _create_layer_shell_window(
        self,
        width: int,
        height: int,
        output_name: Optional[str] = None,
    ) -> int:
        """Create a wlr-layer-shell surface using gtk-layer-shell."""
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, Gtk  # noqa: F401

        import gtk_layer_shell  # type: ignore

        # GTK + gtk-layer-shell initialization
        Gtk.init_check()

        window = Gtk.Window()
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_default_size(width, height)

        # Initialize gtk-layer-shell for this window
        gtk_layer_shell.init_for_window(window)

        # Anchor to all edges (full screen)
        for edge in (
            gtk_layer_shell.Edge.TOP,
            gtk_layer_shell.Edge.BOTTOM,
            gtk_layer_shell.Edge.LEFT,
            gtk_layer_shell.Edge.RIGHT,
        ):
            gtk_layer_shell.set_anchor(window, edge, 0)

        # Set to background layer
        gtk_layer_shell.set_layer(window, gtk_layer_shell.Layer.LAYER_BACKGROUND)

        # Set exclusive zone to keep window at bottom
        gtk_layer_shell.set_exclusive_zone(window, -1)

        # Optionally pin to specific monitor
        if output_name:
            display = window.get_display()
            try:
                monitor = display.get_monitor_by_name(output_name)
                if monitor:
                    gtk_layer_shell.set_monitor(window, monitor)
                    logger.info(f"Pinned wallpaper to monitor: {output_name}")
            except Exception as exc:
                logger.warning(f"Could not set monitor {output_name}: {exc}")

        window.show_all()

        # Get the underlying X11 window ID (works even on Wayland via XWayland)
        # gtk-layer-shell surfaces have an X11 window under XWayland
        try:
            xid = window.get_xid()
        except Exception:
            # Pure Wayland surface - mpv needs special handling
            logger.warning(
                "Could not get X11 XID from layer-shell window. "
                "Pure Wayland mpv embedding requires compositor-specific support."
            )
            xid = 0

        self._window_id = xid
        self._gtk_window = window
        logger.info(f"Created layer-shell wallpaper window, XID={xid}")
        return xid

    def _set_x11_desktop_atoms(self, window: Gtk.Window) -> None:
        """Set X11 atoms so the window manager treats the window as desktop bg."""
        try:
            from gi.repository import Gdk, GdkX11

            gdk_window = window.get_window()
            if gdk_window is None:
                return

            display: GdkX11.X11Display = gdk_window.get_display()  # type: ignore

            # Get required atoms
            net_wm_state = display.get_xatom_by_name("_NET_WM_STATE")
            net_wm_state_below = display.get_xatom_by_name("_NET_WM_STATE_BELOW")
            net_wm_window_type = display.get_xatom_by_name("_NET_WM_WINDOW_TYPE")
            net_wm_type_desktop = display.get_xatom_by_name("_NET_WM_WINDOW_TYPE_DESKTOP")
            motif_hints = display.get_xatom_by_name("_MOTIF_WM_HINTS")

            # Set _NET_WM_WINDOW_TYPE = _NET_WM_WINDOW_TYPE_DESKTOP
            gdk_window.property_change(
                net_wm_window_type,
                Gdk.Atom.intern("ATOM", False),
                8,
                Gdk.PropertyMode.REPLACE,
                [net_wm_type_desktop],
            )

            # Set _MOTIF_WM_HINTS to indicate no decorations
            # Format: {flags, functions, decorations}
            motif_data = [0x2, 0x0, 0x0, 0x0, 0x0]  # MWM_HINTS_DECORATIONS = 0
            gdk_window.property_change(
                motif_hints,
                Gdk.Atom.intern("CARD32", False),
                32,
                Gdk.PropertyMode.REPLACE,
                motif_data,
            )

            # Set _NET_WM_STATE_BELOW
            gdk_window.property_change(
                net_wm_state,
                Gdk.Atom.intern("ATOM", False),
                8,
                Gdk.PropertyMode.APPEND,
                [net_wm_state_below],
            )

            logger.debug("X11 desktop atoms set successfully")

        except Exception as exc:
            logger.warning(f"Could not set X11 desktop atoms: {exc}")
