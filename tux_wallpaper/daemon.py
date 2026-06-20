"""System tray daemon entry point for Tux Wallpaper.

Manages:
- System tray icon with playback controls
- Starting/stopping the local API server
- Launching the web UI window
- Global shortcuts
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import structlog
from platformdirs import PlatformDirs

# Import ui components lazily (requires webview / GTK)
_window = None
_tray = None


def configure_logging(debug: bool = False) -> None:
    """Configure structured logging."""
    log_level = "DEBUG" if debug else "INFO"
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
            if not sys.stderr.isatty()
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
    )


def get_data_dir() -> Path:
    """Get application data directory."""
    dirs = PlatformDirs("tux-wallpaper", "tux-wallpaper")
    data_dir = Path(dirs.user_data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ---------------------------------------------------------------------------
# Tray icon
# ---------------------------------------------------------------------------


def setup_tray() -> None:
    """Create system tray icon and menu."""
    global _tray
    try:
        import gi  # type: ignore

        gi.require_version("Gtk", "3.0")
        gi.require_version("AppIndicator3", "0.1")  # type: ignore
        from gi.repository import AppIndicator3, Gdk, Gtk  # type: ignore
    except ImportError as exc:
        logging.warning(f"Cannot setup tray: {exc}")
        return

    app = Gtk.Application.get_default()
    if app is None:
        app = Gtk.Application.new("com.tuxwallpaper.App", 0)
        app.connect("activate", _on_app_activate)
        app.register()

    indicator = AppIndicator3.Indicator.new(
        "tux-wallpaper",
        "video-display",
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu.new()

    # Now playing
    now_playing_item = Gtk.MenuItem.new_with_label("No wallpaper playing")
    now_playing_item.set_sensitive(False)
    now_playing_item.show()
    menu.append(now_playing_item)

    menu.append(Gtk.SeparatorMenuItem.new())
    menu.append(_make_menu_item("▶ Play", _tray_play))
    menu.append(_make_menu_item("⏸ Pause", _tray_pause))
    menu.append(_make_menu_item("⏹ Stop", _tray_stop))

    menu.append(Gtk.SeparatorMenuItem.new())
    menu.append(_make_menu_item("🖼 Browse Wallpapers...", _tray_open_ui))
    menu.append(_make_menu_item("⚙ Settings", _tray_settings))

    menu.append(Gtk.SeparatorMenuItem.new())
    menu.append(_make_menu_item("❌ Quit", _tray_quit))

    menu.show_all()
    indicator.set_menu(menu)
    _tray = indicator


def _make_menu_item(
    label: str, callback: callable, *args: object
) -> Gtk.MenuItem:
    """Create a menu item with callback."""
    item = Gtk.MenuItem.new_with_label(label)
    item.connect("activate", callback, *args)
    item.show()
    return item


def _tray_play(*args: object) -> None:
    """Handle tray play action."""
    import httpx
    try:
        httpx.post("http://127.0.0.1:18421/api/playback/command", json={"action": "play"})
    except httpx.RequestError:
        pass


def _tray_pause(*args: object) -> None:
    """Handle tray pause action."""
    import httpx
    try:
        httpx.post("http://127.0.0.1:18421/api/playback/command", json={"action": "pause"})
    except httpx.RequestError:
        pass


def _tray_stop(*args: object) -> None:
    """Handle tray stop action."""
    import httpx
    try:
        httpx.post("http://127.0.0.1:18421/api/playback/command", json={"action": "stop"})
    except httpx.RequestError:
        pass


def _tray_open_ui(*args: object) -> None:
    """Open the web UI window.

    Tries pywebview first (native window). Falls back to opening
    the URL in the system's default browser.
    """
    import logging
    import webbrowser

    try:
        import webview  # type: ignore

        global _window
        if _window is None:
            _window = webview.create_window(
                "Tux Wallpaper",
                "http://127.0.0.1:18422",
                width=1200,
                height=800,
                resizable=True,
            )
            webview.start()
            _window = None
    except ImportError:
        logging.info(
            "pywebview not available, opening UI in default browser. "
            "Navigate to http://127.0.0.1:18422"
        )
        webbrowser.open("http://127.0.0.1:18422")


def _tray_settings(*args: object) -> None:
    """Open settings window."""
    # TODO: implement settings window
    pass


def _tray_quit(*args: object) -> None:
    """Quit the application."""
    import httpx
    try:
        httpx.post("http://127.0.0.1:18421/api/shutdown")
    except httpx.RequestError:
        pass
    Gtk.main_quit()
    sys.exit(0)


def _on_app_activate(*args: object) -> None:
    """Handle app activation (GTK app start)."""
    setup_tray()


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------


async def run_api_server(host: str = "127.0.0.1", port: int = 18421) -> None:
    """Run the FastAPI server."""
    import uvicorn
    from tux_wallpaper.service.api import app

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_web_server(
    host: str = "127.0.0.1", port: int = 18422, web_root: Optional[Path] = None
) -> None:
    """Run a simple static file web server for the UI."""
    import os
    from aiohttp import web

    if web_root is None:
        web_root = Path(__file__).parent.parent / "web"

    async def serve_file(request: web.Request) -> web.Response:
        path = request.match_info.get("path", "index.html")
        file_path = web_root / path
        if not file_path.is_file():
            file_path = web_root / "index.html"
        return web.Response(text=file_path.read_text(), content_type="text/html")

    app = web.Application()
    app.router.add_get("/{path:.*}", serve_file)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info(f"Web UI server running at http://{host}:{port}")
    await asyncio.Event().wait()  # Run forever


async def start_servers(
    api_host: str, api_port: int, web_host: str, web_port: int, web_root: Optional[Path]
) -> None:
    """Start both API and web servers."""
    await asyncio.gather(
        run_api_server(api_host, api_port),
        run_web_server(web_host, web_port, web_root),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point for tux-wallpaper daemon."""
    parser = argparse.ArgumentParser(
        description="Tux Wallpaper - Video wallpaper player for Linux"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--api-host", default="127.0.0.1", help="API server host"
    )
    parser.add_argument(
        "--api-port", type=int, default=18421, help="API server port"
    )
    parser.add_argument(
        "--web-host", default="127.0.0.1", help="Web UI server host"
    )
    parser.add_argument(
        "--web-port", type=int, default=18422, help="Web UI server port"
    )
    parser.add_argument(
        "--web-root", type=Path, default=None, help="Web UI root directory"
    )
    parser.add_argument(
        "--no-ui", action="store_true", help="Run without UI (API only)"
    )
    args = parser.parse_args()

    configure_logging(debug=args.debug)

    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def signal_handler(sig: int, frame) -> None:
        logging.info(f"Received signal {sig}, shutting down")
        loop.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Setup GTK app for tray
    if not args.no_ui:
        try:
            import gi  # type: ignore
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
            app = Gtk.Application.new("com.tuxwallpaper.App", 0)
            app.connect("activate", _on_app_activate)
            app.register()
        except ImportError as exc:
            logging.warning(f"Cannot initialize GTK: {exc}. Running without tray.")
            args.no_ui = True

    try:
        if args.no_ui:
            loop.run_until_complete(run_api_server(args.api_host, args.api_port))
        else:
            loop.run_until_complete(
                start_servers(
                    args.api_host,
                    args.api_port,
                    args.web_host,
                    args.web_port,
                    args.web_root,
                )
            )
    except KeyboardInterrupt:
        logging.info("Interrupted, shutting down")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
