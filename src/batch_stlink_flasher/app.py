"""Application bootstrap."""

from __future__ import annotations

import sys


def run(argv: list[str] | None = None) -> int:
    """Start the Qt desktop application."""
    from PySide6.QtWidgets import QApplication

    from batch_stlink_flasher.ui.main_window import MainWindow

    app = QApplication.instance()
    if app is None:
        app = QApplication(argv if argv is not None else sys.argv)
    app.setOrganizationName("BatchSTLinkFlasher")
    app.setApplicationName("BatchSTLinkFlasher")
    window = MainWindow()
    window.show()
    return int(app.exec())
