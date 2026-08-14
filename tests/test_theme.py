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
    from PySide6.QtGui import QPalette

    from batch_stlink_flasher.ui.theme import ThemeMode, active_palette, resolve_palette

    apply_app_theme(qapp, ThemeMode.DARK)
    assert "primaryButton" in qapp.styleSheet()
    assert "QTabWidget::pane" in qapp.styleSheet()
    assert active_palette().name == "dark"
    assert qapp.palette().color(QPalette.ColorRole.Window).name() == active_palette().bg
    apply_app_theme(qapp, ThemeMode.LIGHT)
    assert active_palette().name == "light"
    assert active_palette().bg.lower() == "#f4f6f8"
    assert "primaryButton" in qapp.styleSheet()
    assert qapp.palette().color(QPalette.ColorRole.Window).name().lower() == "#f4f6f8"
    assert resolve_palette(ThemeMode.DARK).name == "dark"
    assert resolve_palette(ThemeMode.LIGHT).name == "light"
    assert not load_app_icon().isNull()
    from batch_stlink_flasher.ui.theme import load_logo_pixmap, load_splash_pixmap

    assert not load_logo_pixmap(max_width=64).isNull()
    assert not load_splash_pixmap(max_width=64).isNull()


def test_build_qpalette_matches_theme() -> None:
    from PySide6.QtGui import QPalette

    from batch_stlink_flasher.ui.theme import DARK, LIGHT, build_qpalette

    dark = build_qpalette(DARK)
    assert dark.color(QPalette.ColorRole.WindowText).name().lower() == DARK.text.lower()
    light = build_qpalette(LIGHT)
    assert light.color(QPalette.ColorRole.Base).name().lower() == LIGHT.bg_input.lower()


def test_normalize_theme_mode() -> None:
    from batch_stlink_flasher.ui.theme import ThemeMode, normalize_theme_mode

    assert normalize_theme_mode("light") is ThemeMode.LIGHT
    assert normalize_theme_mode("DARK") is ThemeMode.DARK
    assert normalize_theme_mode("nope") is ThemeMode.SYSTEM
    assert normalize_theme_mode(None) is ThemeMode.SYSTEM


def test_resolve_system_palette(monkeypatch) -> None:
    from batch_stlink_flasher.ui import theme

    monkeypatch.setattr(theme, "system_prefers_dark", lambda: True)
    assert theme.resolve_palette(theme.ThemeMode.SYSTEM).name == "dark"
    monkeypatch.setattr(theme, "system_prefers_dark", lambda: False)
    assert theme.resolve_palette(theme.ThemeMode.SYSTEM).name == "light"


def test_decorate_button(qapp: QApplication) -> None:
    btn = QPushButton("Flash")
    decorate_button(btn, standard=QStyle.StandardPixmap.SP_DialogApplyButton, role="primary")
    assert btn.objectName() == "primaryButton"
    assert not btn.icon().isNull()


def test_create_browse_button(qapp: QApplication) -> None:
    from batch_stlink_flasher.ui.theme import create_browse_button

    apply_app_theme(qapp, "dark")
    btn = create_browse_button(height=26)
    assert btn.objectName() == "browseButton"
    assert btn.text() == "…"
    assert btn.icon().isNull()
    assert btn.width() == 26 and btn.height() == 26
    assert "QPushButton#browseButton" in qapp.styleSheet()
    btn.close()


def test_path_browse_row_uses_same_browse_button(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QLineEdit, QPushButton

    from batch_stlink_flasher.ui.path_row import path_browse_row

    apply_app_theme(qapp, "dark")
    edit = QLineEdit()
    row = path_browse_row(edit, lambda: None)
    buttons = row.findChildren(QPushButton)
    assert len(buttons) == 1
    assert buttons[0].objectName() == "browseButton"
    assert buttons[0].text() == "…"
    assert buttons[0].size() == buttons[0].size()  # fixed
    assert buttons[0].width() == edit.minimumHeight()
    row.close()


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
