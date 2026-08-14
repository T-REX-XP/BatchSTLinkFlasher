"""Session log view with optional device filter."""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit


class LogView(QPlainTextEdit):
    """Append-only log panel."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(20_000)
        font = QFont("Consolas")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setPlaceholderText("OpenOCD output will appear here...")

    def append_line(self, line: str) -> None:
        self.appendPlainText(line)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def append_device_line(self, serial: str, line: str) -> None:
        self.append_line(f"[{serial}] {line}")

    def clear_log(self) -> None:
        self.clear()
