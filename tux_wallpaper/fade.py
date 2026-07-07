"""Timer-based fade in/out for volume transitions.

This module has no GTK or VLC dependencies and can be imported
without a display environment.
"""

from __future__ import annotations

from threading import Timer
from typing import Callable, Optional


class Fade:
    """Timer-based fade in/out for volume transitions."""

    def __init__(self) -> None:
        self._timer: Optional[Timer] = None
        self._is_active = False

    def start(
        self,
        cur: float,
        target: float,
        step: float,
        fade_interval: float,
        update_callback: Optional[Callable[[int], None]] = None,
        complete_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Start fade from cur to target."""
        self.cancel()
        self._is_active = True
        self._fade_step(cur, target, step, fade_interval, update_callback, complete_callback)

    def _fade_step(
        self,
        cur: float,
        target: float,
        step: float,
        fade_interval: float,
        update_callback: Optional[Callable[[int], None]],
        complete_callback: Optional[Callable[[], None]],
    ) -> None:
        if not self._is_active:
            return

        new_cur = cur + step
        if (step < 0 and new_cur <= target) or (step > 0 and new_cur >= target):
            new_cur = target
            if update_callback:
                update_callback(int(new_cur))
            if complete_callback:
                complete_callback()
            self._is_active = False
            return

        if update_callback:
            update_callback(int(new_cur))

        self._timer = Timer(
            fade_interval,
            self._fade_step,
            args=[new_cur, target, step, fade_interval, update_callback, complete_callback],
        )
        self._timer.daemon = True
        self._timer.start()

    def cancel(self) -> None:
        """Cancel any ongoing fade."""
        self._is_active = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
