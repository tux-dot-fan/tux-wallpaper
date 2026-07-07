"""Configuration management for Tux Wallpaper."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .commons import (
    CONFIG_DIR,
    CONFIG_KEY_BLUR_RADIUS,
    CONFIG_KEY_DATA_SOURCE,
    CONFIG_KEY_FADE_DURATION_SEC,
    CONFIG_KEY_FADE_INTERVAL,
    CONFIG_KEY_FIRST_TIME,
    CONFIG_KEY_MUTE,
    CONFIG_KEY_MUTE_WHEN_MAXIMIZED,
    CONFIG_KEY_MODE,
    CONFIG_KEY_PAUSE_WHEN_MAXIMIZED,
    CONFIG_KEY_STATIC_WALLPAPER,
    CONFIG_KEY_SYSTRAY,
    CONFIG_KEY_VERSION,
    CONFIG_KEY_VOLUME,
    CONFIG_PATH,
    CONFIG_TEMPLATE,
    CONFIG_VERSION,
    MODE_VIDEO,
)

logger = logging.getLogger("TuxWallpaper")


class ConfigUtil:
    """Manages JSON config file for Tux Wallpaper."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load config from file, or generate default if missing/invalid."""
        if not self._check_file():
            self._config = self._generate_template()
            return

        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Config load error: {e}")
            self._config = self._generate_template()
            return

        if not self._check(raw):
            self._config = self._migrate(raw) if self._needs_migrate(raw) else self._generate_template()
        else:
            self._config = raw

    def _check_file(self) -> bool:
        """Check if config file exists."""
        return os.path.isfile(CONFIG_PATH)

    def _check(self, config: dict[str, Any]) -> bool:
        """Check if config is valid."""
        all_keys = all(key in config for key in CONFIG_TEMPLATE)
        version_match = config.get(CONFIG_KEY_VERSION) == CONFIG_VERSION
        return all_keys and version_match

    def _needs_migrate(self, config: dict[str, Any]) -> bool:
        """Check if config needs migration."""
        return config.get(CONFIG_KEY_VERSION, 0) < CONFIG_VERSION

    def _migrate(self, old: dict[str, Any]) -> dict[str, Any]:
        """Migrate old config to current version."""
        old_ver = old.get(CONFIG_KEY_VERSION, 0)

        if old_ver < 4:
            # v3 -> v4: restructure data_source for multi-monitor
            old_source = old.get(CONFIG_KEY_DATA_SOURCE, "")
            old_config = self._generate_template()
            old_config[CONFIG_KEY_DATA_SOURCE]["Default"] = old_source
            # is_detect_maximized -> is_pause_when_maximized
            old_config[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED] = old.get("is_detect_maximized", True)
            old_config[CONFIG_KEY_MUTE_WHEN_MAXIMIZED] = False
            old_config[CONFIG_KEY_VERSION] = 4
            logger.info("Migrated config from v3 to v4")
            self._save(old_config)
            return old_config

        return self._generate_template()

    def _generate_template(self) -> dict[str, Any]:
        """Generate default config and save to disk."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self._save(CONFIG_TEMPLATE.copy())
        return CONFIG_TEMPLATE.copy()

    def _save(self, config: dict[str, Any]) -> None:
        """Save config to disk."""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value and persist."""
        self._config[key] = value
        self._save(self._config)

    @property
    def config(self) -> dict[str, Any]:
        """Full config dict."""
        return self._config.copy()
