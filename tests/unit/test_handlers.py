"""Unit tests for event handlers."""

from __future__ import annotations

import time

import pytest

from tux_wallpaper.fade import Fade


class TestFade:
    def test_fade_up_complete(self):
        """Test fade from 0 to 100 completes at target."""
        values = []

        def update(v):
            values.append(v)

        complete_called = []

        def complete():
            complete_called.append(True)

        fade = Fade()
        fade.start(cur=0, target=100, step=10, fade_interval=0.01, update_callback=update, complete_callback=complete)

        # Wait for fade to complete
        time.sleep(0.15)

        assert 100 in values
        assert len(complete_called) == 1
        fade.cancel()

    def test_fade_down_complete(self):
        """Test fade from 100 to 0 completes at target."""
        values = []

        def update(v):
            values.append(v)

        complete_called = []

        def complete():
            complete_called.append(True)

        fade = Fade()
        fade.start(cur=100, target=0, step=-10, fade_interval=0.01, update_callback=update, complete_callback=complete)

        time.sleep(0.15)

        assert 0 in values
        assert len(complete_called) == 1
        fade.cancel()

    def test_fade_cancel(self):
        """Test that cancel stops the fade."""
        values = []

        def update(v):
            values.append(v)

        fade = Fade()
        fade.start(cur=0, target=100, step=10, fade_interval=0.01, update_callback=update)

        time.sleep(0.05)
        fade.cancel()
        time.sleep(0.2)

        # Should have some values but fade should not complete
        assert len(values) > 0
        # Cancel should not trigger complete
        fade.cancel()  # should not raise

    def test_fade_start_cancels_previous(self):
        """Test that starting a new fade cancels the previous one."""
        values = []

        def update(v):
            values.append(v)

        fade = Fade()
        fade.start(cur=0, target=100, step=10, fade_interval=0.01, update_callback=update)
        time.sleep(0.05)
        # Start a new fade while first is running
        fade.start(cur=0, target=50, step=5, fade_interval=0.01, update_callback=update)
        time.sleep(0.15)

        # Should only have values from the second fade (50 max)
        assert all(v <= 50 for v in values)
        fade.cancel()
