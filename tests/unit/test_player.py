"""Unit tests for the player module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tux_wallpaper.player.mpv_player import (
    MpvPlayer,
    PlaybackState,
    PlayerConfig,
)
from tux_wallpaper.player.window import WallpaperWindow, WindowBackend, WindowConfig


class TestPlayerConfig:
    """Tests for PlayerConfig."""

    def test_default_config(self) -> None:
        """Test default player configuration."""
        config = PlayerConfig()
        assert config.loop is True
        assert config.mute is True
        assert config.hwdec == "auto"
        assert config.vo == "wayland,x11,null"
        assert config.speed == 1.0
        assert config.volume == 0

    def test_custom_config(self) -> None:
        """Test custom player configuration."""
        config = PlayerConfig(
            loop=False,
            mute=False,
            hwdec="vaapi",
            speed=2.0,
        )
        assert config.loop is False
        assert config.mute is False
        assert config.hwdec == "vaapi"
        assert config.speed == 2.0


class TestMpvPlayer:
    """Tests for MpvPlayer."""

    def test_initial_state(self) -> None:
        """Test player starts in stopped state."""
        player = MpvPlayer()
        assert player.state == PlaybackState.STOPPED
        assert player.current_file is None
        assert not player.is_running

    def test_load_nonexistent_file(self) -> None:
        """Test loading a non-existent file raises error."""
        player = MpvPlayer()
        with pytest.raises(FileNotFoundError):
            player.load(Path("/nonexistent/video.mp4"))

    def test_load_valid_file(self, sample_video_path: Path) -> None:
        """Test loading a valid video file."""
        player = MpvPlayer()
        player.load(sample_video_path)
        assert player.current_file == sample_video_path
        assert player.state == PlaybackState.STOPPED

    def test_play_without_load(self) -> None:
        """Test playing without loading a file raises error."""
        player = MpvPlayer()
        with pytest.raises(RuntimeError, match="No video loaded"):
            player.play()

    def test_play_starts_process(self, sample_video_path: Path) -> None:
        """Test play() starts the mpv subprocess."""
        mock_mpv_module = MagicMock()
        mock_mpv_instance = MagicMock()
        mock_mpv_module.MPV.return_value = mock_mpv_instance

        with patch.dict("sys.modules", {"mpv": mock_mpv_module}):
            player = MpvPlayer()
            player.load(sample_video_path)
            player.play()

            assert player.is_running
            assert player.state == PlaybackState.PLAYING

    def test_stop_terminates_process(self, sample_video_path: Path) -> None:
        """Test stop() terminates the mpv subprocess."""
        mock_mpv_module = MagicMock()
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.window_alive = True
        mock_mpv_module.MPV.return_value = mock_mpv_instance

        with patch.dict("sys.modules", {"mpv": mock_mpv_module}):
            player = MpvPlayer()
            player.load(sample_video_path)
            player.play()
            player.stop()

            assert player.state == PlaybackState.STOPPED
            assert not player.is_running

    def test_pause_updates_state(self, sample_video_path: Path) -> None:
        """Test pause() updates state to paused."""
        mock_mpv_module = MagicMock()
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.window_alive = True
        mock_mpv_instance.pause = False
        mock_mpv_module.MPV.return_value = mock_mpv_instance

        with patch.dict("sys.modules", {"mpv": mock_mpv_module}):
            player = MpvPlayer()
            player.load(sample_video_path)
            player.play()
            player.pause()

            assert player.state == PlaybackState.PAUSED

    def test_toggle_pause_from_playing(self, sample_video_path: Path) -> None:
        """Test toggle_pause() from playing state."""
        mock_mpv_module = MagicMock()
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.window_alive = True
        mock_mpv_instance.pause = False
        mock_mpv_module.MPV.return_value = mock_mpv_instance

        with patch.dict("sys.modules", {"mpv": mock_mpv_module}):
            player = MpvPlayer()
            player.load(sample_video_path)
            player.play()
            assert player.state == PlaybackState.PLAYING

            player.toggle_pause()
            assert player.state == PlaybackState.PAUSED

            player.toggle_pause()
            assert player.state == PlaybackState.PLAYING

    def test_set_speed(self, sample_video_path: Path) -> None:
        """Test setting playback speed."""
        player = MpvPlayer()
        player.config.speed = 1.0
        player.set_speed(2.0)
        assert player.config.speed == 2.0

    def test_set_loop(self, sample_video_path: Path) -> None:
        """Test enabling/disabling loop."""
        player = MpvPlayer()
        assert player.config.loop is True
        player.set_loop(False)
        assert player.config.loop is False
        player.set_loop(True)
        assert player.config.loop is True

    def test_state_callback(self, sample_video_path: Path) -> None:
        """Test state change callback is called."""
        mock_mpv_module = MagicMock()
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.window_alive = True
        mock_mpv_module.MPV.return_value = mock_mpv_instance

        with patch.dict("sys.modules", {"mpv": mock_mpv_module}):
            player = MpvPlayer()
            callback = MagicMock()
            player.set_state_callback(callback)

            player.load(sample_video_path)
            player.play()

            assert callback.called

    def test_close_cleans_up(self, sample_video_path: Path) -> None:
        """Test close() stops process and clears callbacks."""
        mock_mpv_module = MagicMock()
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.window_alive = True
        mock_mpv_module.MPV.return_value = mock_mpv_instance

        with patch.dict("sys.modules", {"mpv": mock_mpv_module}):
            player = MpvPlayer()
            callback = MagicMock()
            player.set_state_callback(callback)

            player.load(sample_video_path)
            player.play()
            player.close()

            assert player.state == PlaybackState.STOPPED
            assert not player.is_running
            assert len(player._state_callbacks) == 0


class TestPlaybackState:
    """Tests for PlaybackState enum."""

    def test_all_states_exist(self) -> None:
        """Test all expected states are defined."""
        assert PlaybackState.STOPPED.value == "stopped"
        assert PlaybackState.PLAYING.value == "playing"
        assert PlaybackState.PAUSED.value == "paused"
        assert PlaybackState.ERROR.value == "error"


class TestWindowConfig:
    """Tests for WindowConfig."""

    def test_default_config(self) -> None:
        """Test default window configuration."""
        config = WindowConfig()
        assert config.backend == WindowBackend.AUTO
        assert config.fullscreen is True
        assert config.layer == "background"

    def test_custom_config(self) -> None:
        """Test custom window configuration."""
        config = WindowConfig(
            backend=WindowBackend.X11,
            fullscreen=True,
            geometry="1920x1080",
        )
        assert config.backend == WindowBackend.X11
        assert config.geometry == "1920x1080"


class TestWallpaperWindow:
    """Tests for WallpaperWindow."""

    def test_auto_backend_detection(self) -> None:
        """Test window backend is auto-detected."""
        window = WallpaperWindow()
        # Backend should be detected from environment
        assert window.config.backend in (WindowBackend.WAYLAND, WindowBackend.X11)

    def test_window_id_initially_none(self) -> None:
        """Test window ID is None before creation."""
        window = WallpaperWindow()
        assert window.window_id is None

    def test_close_when_not_created(self) -> None:
        """Test close() is safe when window not created."""
        window = WallpaperWindow()
        window.close()  # Should not raise
        assert window.window_id is None
