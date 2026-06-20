"""Test fixtures and configuration for Tux Wallpaper tests."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(temp_dir: Path) -> Path:
    """Provide a path to a temporary database file."""
    return temp_dir / "test.db"


@pytest.fixture
def sample_video_path(temp_dir: Path) -> Path:
    """Create a dummy video file for testing."""
    video_path = temp_dir / "sample.mp4"
    video_path.write_bytes(b"fake video content for testing")
    return video_path


@pytest.fixture
def mock_mpv(mocker):
    """Mock the mpv subprocess."""
    mock_process = mocker.MagicMock()
    mock_process.poll.return_value = None  # Process is running
    mocker.patch("subprocess.Popen", return_value=mock_process)
    return mock_process
