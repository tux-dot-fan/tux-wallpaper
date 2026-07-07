"""Unit tests for commons constants."""

from __future__ import annotations

from tux_wallpaper.commons import (
    CONFIG_KEY_BLUR_RADIUS,
    CONFIG_KEY_DATA_SOURCE,
    CONFIG_KEY_FADE_DURATION_SEC,
    CONFIG_KEY_FADE_INTERVAL,
    CONFIG_KEY_FIRST_TIME,
    CONFIG_KEY_MODE,
    CONFIG_KEY_MUTE,
    CONFIG_KEY_MUTE_WHEN_MAXIMIZED,
    CONFIG_KEY_PAUSE_WHEN_MAXIMIZED,
    CONFIG_KEY_STATIC_WALLPAPER,
    CONFIG_KEY_SYSTRAY,
    CONFIG_KEY_VERSION,
    CONFIG_KEY_VOLUME,
    CONFIG_TEMPLATE,
    CONFIG_VERSION,
    DBUS_NAME_PLAYER,
    LOGGER_NAME,
    MODE_NULL,
    MODE_VIDEO,
    MODE_STREAM,
    MODE_WEBPAGE,
    PROJECT,
)


class TestConstants:
    def test_logger_name(self):
        assert LOGGER_NAME == "TuxWallpaper"

    def test_project_name(self):
        assert PROJECT == "io.github.tux_wallpaper"

    def test_dbus_name(self):
        assert DBUS_NAME_PLAYER == "io.github.tux_wallpaper.player"

    def test_config_version(self):
        assert CONFIG_VERSION == 4
        assert CONFIG_TEMPLATE[CONFIG_KEY_VERSION] == CONFIG_VERSION

    def test_modes(self):
        assert MODE_NULL == "MODE_NULL"
        assert MODE_VIDEO == "MODE_VIDEO"
        assert MODE_STREAM == "MODE_STREAM"
        assert MODE_WEBPAGE == "MODE_WEBPAGE"

    def test_config_keys_exist(self):
        assert CONFIG_KEY_VERSION in CONFIG_TEMPLATE
        assert CONFIG_KEY_MODE in CONFIG_TEMPLATE
        assert CONFIG_KEY_DATA_SOURCE in CONFIG_TEMPLATE
        assert CONFIG_KEY_MUTE in CONFIG_TEMPLATE
        assert CONFIG_KEY_VOLUME in CONFIG_TEMPLATE
        assert CONFIG_KEY_STATIC_WALLPAPER in CONFIG_TEMPLATE
        assert CONFIG_KEY_BLUR_RADIUS in CONFIG_TEMPLATE
        assert CONFIG_KEY_PAUSE_WHEN_MAXIMIZED in CONFIG_TEMPLATE
        assert CONFIG_KEY_MUTE_WHEN_MAXIMIZED in CONFIG_TEMPLATE
        assert CONFIG_KEY_FADE_DURATION_SEC in CONFIG_TEMPLATE
        assert CONFIG_KEY_FADE_INTERVAL in CONFIG_TEMPLATE
        assert CONFIG_KEY_SYSTRAY in CONFIG_TEMPLATE
        assert CONFIG_KEY_FIRST_TIME in CONFIG_TEMPLATE

    def test_config_defaults(self):
        assert CONFIG_TEMPLATE[CONFIG_KEY_MODE] == MODE_NULL
        assert CONFIG_TEMPLATE[CONFIG_KEY_MUTE] is False
        assert CONFIG_TEMPLATE[CONFIG_KEY_VOLUME] == 50
        assert CONFIG_TEMPLATE[CONFIG_KEY_STATIC_WALLPAPER] is True
        assert CONFIG_TEMPLATE[CONFIG_KEY_BLUR_RADIUS] == 5
        assert CONFIG_TEMPLATE[CONFIG_KEY_PAUSE_WHEN_MAXIMIZED] is True
        assert CONFIG_TEMPLATE[CONFIG_KEY_MUTE_WHEN_MAXIMIZED] is False
        assert CONFIG_TEMPLATE[CONFIG_KEY_FADE_DURATION_SEC] == 1.5
        assert CONFIG_TEMPLATE[CONFIG_KEY_FADE_INTERVAL] == 0.1
        assert CONFIG_TEMPLATE[CONFIG_KEY_SYSTRAY] is False
        assert CONFIG_TEMPLATE[CONFIG_KEY_FIRST_TIME] is True
        assert isinstance(CONFIG_TEMPLATE[CONFIG_KEY_DATA_SOURCE], dict)
