"""Startup splash that scans for ST-Link adapters before the main window."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from batch_stlink_flasher import __version__, __version_info__
from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.ui.theme import ACCENT, BG, BORDER, TEXT, TEXT_MUTED, load_logo_pixmap
from batch_stlink_flasher.ui.workers import DiscoveryWorker


class SplashScreen(QWidget):
    """
    Frameless splash shown at startup while USB/ST-Link discovery runs.

    Emits ``scan_finished(adapters, error)`` when the scan completes.
    ``error`` is an empty string on success.
    """

    scan_finished = Signal(list, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Batch ST-Link Flasher {__version__}")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setFixedSize(460, 360)
        self.setObjectName("splashRoot")
        self.setStyleSheet(
            f"""
            QWidget#splashRoot {{
                background-color: {BG};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
            QLabel#title {{
                color: {TEXT};
                font-size: 20px;
                font-weight: 700;
            }}
            QLabel#subtitle {{
                color: {TEXT_MUTED};
                font-size: 12px;
            }}
            QLabel#status {{
                color: {TEXT};
                font-size: 13px;
            }}
            QProgressBar {{
                border: 1px solid {BORDER};
                border-radius: 4px;
                background: #12161e;
                text-align: center;
                color: {TEXT};
                min-height: 16px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT};
                border-radius: 3px;
            }}
            """
        )

        art = QLabel()
        art.setObjectName("splashArt")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setPixmap(load_logo_pixmap(max_width=128))

        title = QLabel("Batch ST-Link Flasher")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if len(__version_info__) >= 4:
            ver_text = (
                f"v{__version_info__[0]}.{__version_info__[1]}.{__version_info__[2]} "
                f"· build {__version_info__[3]}"
            )
        else:
            ver_text = f"v{__version__}"
        subtitle = QLabel(ver_text)
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Scanning for ST-Link programmers...")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setTextVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)
        layout.addStretch(1)
        layout.addWidget(art)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self._worker: DiscoveryWorker | None = None
        self._adapters: list[AdapterInfo] = []
        self._error = ""

    def center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(
            geo.center().x() - self.width() // 2,
            geo.center().y() - self.height() // 2,
        )

    def start_scan(self) -> None:
        """Begin device discovery on a background thread."""
        if self._worker is not None and self._worker.isRunning():
            return
        self.status_label.setText("Scanning for ST-Link programmers...")
        self.progress.setRange(0, 0)
        worker = DiscoveryWorker()
        worker.finished_ok.connect(self._on_ok)
        worker.failed.connect(self._on_failed)
        self._worker = worker
        worker.start()

    def _on_ok(self, adapters: list) -> None:
        self._adapters = list(adapters)
        self._error = ""
        count = len(self._adapters)
        if count == 0:
            self.status_label.setText("No ST-Link adapters found.")
        elif count == 1:
            self.status_label.setText("Found 1 ST-Link adapter.")
        else:
            self.status_label.setText(f"Found {count} ST-Link adapters.")
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.scan_finished.emit(self._adapters, "")

    def _on_failed(self, message: str) -> None:
        self._adapters = []
        self._error = message or "Discovery failed"
        self.status_label.setText(f"Scan failed: {self._error}")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_finished.emit([], self._error)
