"""Application bootstrap with startup splash device scan."""

from __future__ import annotations

import sys


def run(argv: list[str] | None = None) -> int:
    """Start the Qt desktop application."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from batch_stlink_flasher.services.settings import load_settings
    from batch_stlink_flasher.ui.main_window import MainWindow
    from batch_stlink_flasher.ui.splash_screen import SplashScreen
    from batch_stlink_flasher.ui.theme import ThemeMode, apply_app_theme, normalize_theme_mode

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setOrganizationName("BatchSTLinkFlasher")
    app.setApplicationName("BatchSTLinkFlasher")

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

    splash = SplashScreen()
    state["splash"] = splash
    splash.center_on_screen()
    splash.show()
    splash.raise_()
    app.processEvents()

    def _open_main(adapters: list, error: str) -> None:
        # Close splash first so the main window never appears underneath it.
        splash.hide()
        splash.close()
        app.processEvents()

        window = MainWindow(initial_adapters=adapters, initial_scan_error=error or None)
        state["window"] = window
        # Defer show one tick so splash teardown paints first.
        def _show_main() -> None:
            window.show()
            window.raise_()
            window.activateWindow()

        QTimer.singleShot(0, _show_main)

    splash.scan_finished.connect(_open_main)
    splash.start_scan()
    return int(app.exec())
