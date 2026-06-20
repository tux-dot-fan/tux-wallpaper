"""Full-screen window management for wallpaper display on Wayland/X11."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WindowBackend(Enum):
    """Supported window backends."""

    WAYLAND = "wayland"
    X11 = "x11"
    AUTO = "auto"


@dataclass
class WindowConfig:
    """Configuration for wallpaper window."""

    backend: WindowBackend = WindowBackend.AUTO
    fullscreen: bool = True
    layer: str = "background"  # wayland: background, bottom
    geometry: Optional[str] = None  # e.g., "0x0" for fullscreen override


@dataclass
class WallpaperWindow:
    """Manages a full-screen window for wallpaper display.

    On Wayland, uses wlr-layer-shell to place window below normal windows.
    On X11, uses _NET_WM_WINDOW_TYPE to set as desktop background.
    """

    config: WindowConfig = field(default_factory=WindowConfig)
    _window_id: Optional[int] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self._detect_backend()

    def _detect_backend(self) -> None:
        """Detect available window system."""
        if self.config.backend != WindowBackend.AUTO:
            return

        wayland_display = self._run_command(
            ["pgrep", "-x", "gnome-shell"], check=False
        )
        if wayland_display.returncode == 0:
            self.config.backend = WindowBackend.WAYLAND
            logger.info("Detected Wayland session (GNOME)")
            return

        x11_display = self._run_command(
            ["pgrep", "-x", "Xorg"], check=False
        )
        if x11_display.returncode == 0:
            self.config.backend = WindowBackend.X11
            logger.info("Detected X11 session")
            return

        self.config.backend = WindowBackend.X11
        logger.warning("Could not detect session type, falling back to X11")

    def _run_command(
        self, cmd: list[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a shell command, optionally ignoring errors."""
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

    def create(
        self,
        width: int,
        height: int,
        output_name: Optional[str] = None,
    ) -> int:
        """Create a full-screen window.

        Returns the window ID (X11) or layer-shell surface (Wayland).

        Args:
            width: Window width in pixels
            height: Window height in pixels
            output_name: Specific output to create window on (Wayland)

        Returns:
            Window identifier
        """
        logger.info(
            f"Creating wallpaper window: {width}x{height} on {self.config.backend.value}"
        )

        if self.config.backend == WindowBackend.WAYLAND:
            return self._create_wayland_window(width, height, output_name)
        else:
            return self._create_x11_window(width, height)

    def _create_wayland_window(
        self,
        width: int,
        height: int,
        output_name: Optional[str] = None,
    ) -> int:
        """Create Wayland layer-shell window using gtk-layer-shell."""
        try:
            import gtk_layer_shell  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "gtk-layer-shell is required for Wayland support. "
                "Install with: pip install gtk-layer-shell"
            ) from exc

        window = gtk_layer_shell.new()
        gtk_layer_shell.set_layer(window, gtk_layer_shell.Layer.LAYER_BACKGROUND)
        gtk_layer_shell.set_anchor(
            window,
            gtk_layer_shell.Edge.TOP,
            gtk_layer_shell.Edge.BOTTOM,
            gtk_layer_shell.Edge.LEFT,
            gtk_layer_shell.Edge.RIGHT,
        )
        gtk_layer_shell.set_exclusive_zone(window, -1)

        if output_name:
            monitor = self._get_wayland_monitor(output_name)
            if monitor:
                gtk_layer_shell.set_monitor(window, monitor)

        window.show_all()
        self._window_id = window.get_id()
        return self._window_id

    def _create_x11_window(self, width: int, height: int) -> int:
        """Create X11 window using GTK3 with _NET_WM_WINDOW_TYPE."""
        import gi  # type: ignore

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, GdkX11, Gtk  # type: ignore

        Gtk.init([])

        window = Gtk.Window()
        window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_default_size(width, height)

        screen = Gdk.Screen.get_default()
        if screen:
            visual = screen.get_rgba_visual()
            if visual:
                window.set_visual(visual)

        window.realize()
        window.move(0, 0)

        xid = window.get_xid()
        self._window_id = xid

        self._set_x11_atoms(window)

        return xid

    def _set_x11_atoms(self, window: Gtk.Window) -> None:
        """Set X11 atoms for desktop window type."""
        from gi.repository import GdkX11, Gtk  # type: ignore

        display = GdkX11.X11Display.get_default()
        xid = window.get_xid()

        atom_names = [
            "_NET_WM_WINDOW_TYPE_DESKTOP",
            "_NET_WM_STATE_BELOW",
            "_MOTIF_WM_HINTS",
        ]

        for name in atom_names:
            atom = display.get_xatom_by_name(name)
            Gdk.property_change(
                window.get_window(),
                display.get_xatom_by_name("_NET_WM_STATE"),
                Gdk.Atom.intern("ATOM", False),
                8,
                Gdk.PropertyMode.REPLACE,
                [atom],
            )

    def _get_wayland_monitor(self, output_name: str):
        """Get Wayland monitor by name."""
        try:
            import gi  # type: ignore

            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk  # type: ignore
        except ImportError:
            return None

        display = Gtk.Window().get_display()
        monitor = display.get_monitor_by_name(output_name)
        return monitor

    @property
    def window_id(self) -> Optional[int]:
        """Get current window ID."""
        return self._window_id

    def close(self) -> None:
        """Close the wallpaper window."""
        if self._window_id is not None:
            logger.info(f"Closing wallpaper window {self._window_id}")
            self._window_id = None
