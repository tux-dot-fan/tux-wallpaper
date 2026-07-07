"""Unit tests for config management."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from tux_wallpaper.config import ConfigUtil
from tux_wallpaper.commons import CONFIG_KEY_VERSION


class TestConfigUtil:
    def test_generate_default_config(self, tmp_path):
        """Test that a default config is generated when no file exists."""
        config_path = tmp_path / "config.json"

        # Patch CONFIG_PATH to use our temp path
        import tux_wallpaper.config as config_module

        original = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = str(config_path)

        try:
            cfg = ConfigUtil()
            assert cfg.get(CONFIG_KEY_VERSION) == 4
            assert os.path.exists(config_path)
        finally:
            config_module.CONFIG_PATH = original

    def test_load_existing_config(self, tmp_path):
        """Test loading a valid existing config file."""
        config_path = tmp_path / "config.json"
        data = {
            "version": 4,
            "mode": "MODE_VIDEO",
            "data_source": {},
            "is_mute": False,
            "audio_volume": 50,
            "is_static_wallpaper": True,
            "static_wallpaper_blur_radius": 5,
            "is_pause_when_maximized": True,
            "is_mute_when_maximized": False,
            "fade_duration_sec": 1.5,
            "fade_interval": 0.1,
            "is_show_systray": False,
            "is_first_time": False,
        }
        config_path.write_text(json.dumps(data))

        import tux_wallpaper.config as config_module

        original = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = str(config_path)

        try:
            cfg = ConfigUtil()
            assert cfg.get("mode") == "MODE_VIDEO"
            assert cfg.get("audio_volume") == 50
        finally:
            config_module.CONFIG_PATH = original

    def test_get_default(self, tmp_path):
        """Test getting a non-existent key returns default."""
        config_path = tmp_path / "config.json"

        import tux_wallpaper.config as config_module

        original = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = str(config_path)

        try:
            cfg = ConfigUtil()
            assert cfg.get("nonexistent", "default") == "default"
            assert cfg.get("audio_volume") == 50  # from default template
        finally:
            config_module.CONFIG_PATH = original

    def test_set_and_persist(self, tmp_path):
        """Test setting a value persists to disk."""
        config_path = tmp_path / "config.json"

        import tux_wallpaper.config as config_module

        original = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = str(config_path)

        try:
            cfg = ConfigUtil()
            cfg.set("audio_volume", 75)
            assert cfg.get("audio_volume") == 75

            # Reload and verify persistence
            cfg2 = ConfigUtil()
            assert cfg2.get("audio_volume") == 75
        finally:
            config_module.CONFIG_PATH = original

    def test_migrate_v3_to_v4(self, tmp_path):
        """Test migration from v3 config to v4."""
        config_path = tmp_path / "config.json"
        # Old v3 config without version field
        old_data = {
            "mode": "MODE_VIDEO",
            "data_source": "/path/to/video.mp4",
            "is_mute": False,
            "audio_volume": 50,
            "is_detect_maximized": True,
        }
        config_path.write_text(json.dumps(old_data))

        import tux_wallpaper.config as config_module

        original = config_module.CONFIG_PATH
        config_module.CONFIG_PATH = str(config_path)

        try:
            cfg = ConfigUtil()
            # Should migrate to v4
            assert cfg.get(CONFIG_KEY_VERSION) == 4
            assert cfg.get("data_source", {}).get("Default") == "/path/to/video.mp4"
            assert cfg.get("is_pause_when_maximized") is True
        finally:
            config_module.CONFIG_PATH = original
