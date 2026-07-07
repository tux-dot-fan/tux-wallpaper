"""Unit tests for utility functions."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from tux_wallpaper.utils import (
    is_flatpak,
    is_gnome,
    is_nvidia_proprietary,
    is_vdpau_ok,
    is_wayland,
    is_x11,
)


class TestIsFunctions:
    def test_is_gnome_true(self):
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}):
            assert is_gnome() is True

    def test_is_gnome_ubuntu(self):
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "ubuntu:GNOME"}):
            assert is_gnome() is True

    def test_is_gnome_false(self):
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}):
            assert is_gnome() is False

    def test_is_gnome_empty(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("XDG_CURRENT_DESKTOP", None)
            assert is_gnome() is False

    def test_is_wayland_true(self):
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            assert is_wayland() is True

    def test_is_wayland_false(self):
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            assert is_wayland() is False

    def test_is_x11_true(self):
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            assert is_x11() is True

    def test_is_x11_false(self):
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            assert is_x11() is False

    def test_is_flatpak_true(self):
        with patch("os.path.isfile", return_value=True) as m:
            assert is_flatpak() is True
            m.assert_called_once_with("/.flatpak-info")

    def test_is_flatpak_false(self):
        with patch("os.path.isfile", return_value=False) as m:
            assert is_flatpak() is False
            m.assert_called_once_with("/.flatpak-info")

    def test_is_nvidia_proprietary_found(self):
        with patch("subprocess.check_output") as m:
            m.return_value = "OpenGL vendor string: NVIDIA Corporation"
            assert is_nvidia_proprietary() is True

    def test_is_nvidia_proprietary_not_found(self):
        with patch("subprocess.check_output") as m:
            m.return_value = "OpenGL vendor string: AMD"
            assert is_nvidia_proprietary() is False

    def test_is_nvidia_proprietary_command_missing(self):
        with patch(
            "subprocess.check_output",
            side_effect=FileNotFoundError,
        ):
            assert is_nvidia_proprietary() is False

    def test_is_vdpau_ok_success(self):
        with patch("subprocess.run") as m:
            m.return_value = type("obj", (object,), {"returncode": 0})()
            assert is_vdpau_ok() is True

    def test_is_vdpau_ok_failure(self):
        with patch("subprocess.run") as m:
            m.return_value = type("obj", (object,), {"returncode": 1})()
            assert is_vdpau_ok() is False

    def test_is_vdpau_ok_command_missing(self):
        with patch(
            "subprocess.run",
            side_effect=FileNotFoundError,
        ):
            assert is_vdpau_ok() is False
