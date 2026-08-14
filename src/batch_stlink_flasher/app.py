"""Application bootstrap."""

from __future__ import annotations

import sys


def run() -> int:
    """Start the Qt desktop application."""
    from PySide6.QtWidgets import QApplication

    from batch_stlink_flasher.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setOrganizationName("BatchSTLinkFlasher")
    app.setApplicationName("BatchSTLinkFlasher")
    window = MainWindow()
    window.show()
    return app.exec()
