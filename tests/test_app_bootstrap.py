"""Tests for application bootstrap helpers."""

from __future__ import annotations

import os
import sys

from batch_stlink_flasher.app import _prepare_qt_environment


def test_prepare_qt_environment_ignores_dev(monkeypatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _prepare_qt_environment()
    assert os.environ.get("QT_QPA_PLATFORM") == "offscreen"


def test_prepare_qt_environment_clears_offscreen_when_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _prepare_qt_environment()
    assert "QT_QPA_PLATFORM" not in os.environ


def test_prepare_qt_environment_keeps_other_platforms_when_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("QT_QPA_PLATFORM", "windows")
    _prepare_qt_environment()
    assert os.environ.get("QT_QPA_PLATFORM") == "windows"
