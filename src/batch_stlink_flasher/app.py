"""Application bootstrap with startup splash device scan."""

from __future__ import annotations

import sys


def run(argv: list[str] | None = None) -> int:
    """Start the Qt desktop application."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from batch_stlink_flasher.ui.main_window import MainWindow
    from batch_stlink_flasher.ui.splash_screen import SplashScreen

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setOrganizationName("BatchSTLinkFlasher")
    app.setApplicationName("BatchSTLinkFlasher")

    from batch_stlink_flasher.ui.theme import apply_app_theme

    apply_app_theme(app)

    state: dict[str, object] = {"window": None, "splash": None}

    splash = SplashScreen()
    state["splash"] = splash
    splash.center_on_screen()
    splash.show()
    app.processEvents()

    def _open_main(adapters: list, error: str) -> None:
        window = MainWindow(initial_adapters=adapters, initial_scan_error=error or None)
        state["window"] = window
        window.show()
        window.raise_()
        window.activateWindow()
        # Keep splash visible briefly so the user can read the result, then close.
        QTimer.singleShot(450, splash.close)

    splash.scan_finished.connect(_open_main)
    splash.start_scan()
    return int(app.exec())
