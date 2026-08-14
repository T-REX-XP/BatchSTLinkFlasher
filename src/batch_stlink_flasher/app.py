"""Application bootstrap with startup splash device scan."""

from __future__ import annotations

import os
import sys


def _prepare_qt_environment() -> None:
    """
    Frozen builds must never inherit ``QT_QPA_PLATFORM=offscreen`` from a
    developer shell (pytest / CI). That makes the EXE look like it \"won't run\"
    — process alive, no visible window.
    """
    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("QT_QPA_PLATFORM", "").strip().lower() == "offscreen":
        os.environ.pop("QT_QPA_PLATFORM", None)


def run(argv: list[str] | None = None) -> int:
    """Start the Qt desktop application."""
    _prepare_qt_environment()

    # Before any HWND: otherwise taskbar/Alt+Tab keep the python.exe icon.
    from batch_stlink_flasher.util.win_shell import set_app_user_model_id

    set_app_user_model_id()

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from batch_stlink_flasher.services.settings import load_settings
    from batch_stlink_flasher.ui.main_window import MainWindow
    from batch_stlink_flasher.ui.splash_screen import SplashScreen
    from batch_stlink_flasher.ui.theme import ThemeMode, apply_app_theme, load_app_icon, normalize_theme_mode

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setOrganizationName("BatchSTLinkFlasher")
    app.setApplicationName("BatchSTLinkFlasher")
    app.setDesktopFileName("BatchSTLinkFlasher")
    icon = load_app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    settings = load_settings()
    theme_mode = normalize_theme_mode(settings.theme_mode)
    apply_app_theme(app, theme_mode)

    # Follow OS light/dark changes when preference is System.
    def _on_system_color_scheme_changed(_scheme) -> None:
        current = normalize_theme_mode(load_settings().theme_mode)
        if current is ThemeMode.SYSTEM:
            apply_app_theme(app, ThemeMode.SYSTEM)

    app.styleHints().colorSchemeChanged.connect(_on_system_color_scheme_changed)

    state: dict[str, object] = {"window": None, "splash": None}

    # Avoid quitting when splash closes before the main window is shown.
    app.setQuitOnLastWindowClosed(False)

    splash = SplashScreen()
    state["splash"] = splash
    splash.center_on_screen()
    splash.show()
    splash.raise_()
    app.processEvents()

    def _open_main(adapters: list, error: str) -> None:
        window = MainWindow(initial_adapters=adapters, initial_scan_error=error or None)
        state["window"] = window

        def _show_main() -> None:
            window.show()
            window.raise_()
            window.activateWindow()
            splash.hide()
            splash.close()
            app.setQuitOnLastWindowClosed(True)

        # Show main first, then tear down splash (no quit-on-last-window race).
        QTimer.singleShot(0, _show_main)

    splash.scan_finished.connect(_open_main)
    splash.start_scan()
    return int(app.exec())
