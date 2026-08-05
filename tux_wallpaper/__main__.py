"""Tux Wallpaper main entry point.

Usage:
    tux-wallpaper          # Run with GUI (default)
    tux-wallpaper -b       # Run in background (daemon mode)
    tux-wallpaper -h       # Show help
"""

from __future__ import annotations

import argparse
import logging
import sys

from tux_wallpaper.player.video_player import VideoPlayer

LOGGER_NAME = "TuxWallpaper"


def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="tux-wallpaper")
    parser.add_argument(
        "-b",
        "--background",
        action="store_true",
        help="Run in background (daemon mode)",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    setup_logging(debug=args.debug)

    if args.background:
        # Fork to background
        import os

        pid = os.fork()
        if pid != 0:
            # Parent exits
            sys.exit(0)

    app = VideoPlayer()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
