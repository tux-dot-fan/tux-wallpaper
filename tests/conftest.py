"""Pytest fixtures for Tux Wallpaper tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_video_path(temp_dir):
    """Provide a mock video file path."""
    video_path = temp_dir / "test_video.mp4"
    # Create an empty file (not a real video, but exists)
    video_path.write_bytes(b"\x00\x00\x00\x00")
    return video_path
