"""UI theme / asset packaging tests."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton, QStyle

from batch_stlink_flasher.assets_util import asset_path
from batch_stlink_flasher.ui.theme import (
    apply_app_theme,
    decorate_button,
    load_app_icon,
    load_splash_pixmap,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_assets_exist() -> None:
    splash = asset_path("splash.png")
    icon = asset_path("app_icon.png")
    ico = asset_path("app_icon.ico")
    logo = asset_path("logo.png")
    assert splash is not None and splash.is_file()
    assert icon is not None and icon.is_file()
    assert ico is not None and ico.is_file()
    assert logo is not None and logo.is_file()


def test_theme_loads(qapp: QApplication) -> None:
    apply_app_theme(qapp)
    assert "primaryButton" in qapp.styleSheet()
    assert not load_app_icon().isNull()
    from batch_stlink_flasher.ui.theme import load_logo_pixmap, load_splash_pixmap

    assert not load_logo_pixmap(max_width=64).isNull()
    assert not load_splash_pixmap(max_width=64).isNull()


def test_decorate_button(qapp: QApplication) -> None:
    btn = QPushButton("Flash")
    decorate_button(btn, standard=QStyle.StandardPixmap.SP_DialogApplyButton, role="primary")
    assert btn.objectName() == "primaryButton"
    assert not btn.icon().isNull()


def test_theme_fallbacks(qapp: QApplication, monkeypatch, tmp_path) -> None:
    from batch_stlink_flasher.ui import theme

    monkeypatch.setattr(theme, "asset_path", lambda _name: None)
    pix = theme.load_splash_pixmap(max_width=48)
    assert not pix.isNull()
    assert theme.load_app_icon().isNull()

    bad = tmp_path / "missing.png"
    monkeypatch.setattr(theme, "asset_path", lambda _name: bad)
    assert theme.load_app_icon().isNull()
    assert not theme.load_splash_pixmap(max_width=32).isNull()


def test_assets_util_meipass(monkeypatch, tmp_path) -> None:
    import batch_stlink_flasher.assets_util as assets_util

    assets = tmp_path / "batch_stlink_flasher" / "assets"
    assets.mkdir(parents=True)
    target = assets / "splash.png"
    target.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(assets_util.sys, "_MEIPASS", str(tmp_path), raising=False)
    path = assets_util.asset_path("splash.png")
    assert path == target
