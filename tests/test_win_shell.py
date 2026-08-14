"""Tests for Windows shell identity helpers."""

from __future__ import annotations

import sys

from batch_stlink_flasher.util.win_shell import APP_USER_MODEL_ID, set_app_user_model_id


def test_app_user_model_id_constant() -> None:
    assert APP_USER_MODEL_ID.startswith("BatchSTLinkFlasher")


def test_set_app_user_model_id_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert set_app_user_model_id() is False


def test_set_app_user_model_id_windows_ok(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    import ctypes

    class _Ok:
        @staticmethod
        def SetCurrentProcessExplicitAppUserModelID(_app_id: str) -> int:
            return 0

    monkeypatch.setattr(ctypes, "windll", type("W", (), {"shell32": _Ok()})())
    assert set_app_user_model_id("BatchSTLinkFlasher.Test") is True


def test_set_app_user_model_id_windows_failure(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    import ctypes

    class _Fail:
        @staticmethod
        def SetCurrentProcessExplicitAppUserModelID(_app_id: str) -> int:
            return 1

    monkeypatch.setattr(ctypes, "windll", type("W", (), {"shell32": _Fail()})())
    assert set_app_user_model_id() is False
