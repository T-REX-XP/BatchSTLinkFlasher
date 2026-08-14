"""About dialog for Batch ST-Link Flasher."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from batch_stlink_flasher import __version__, __version_info__
from batch_stlink_flasher.ui.theme import load_app_icon, load_logo_pixmap


class AboutDialog(QDialog):
    """Modal About box with version and project summary."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Batch ST-Link Flasher")
        self.setModal(True)
        self.setMinimumWidth(440)
        icon = load_app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)

        art = QLabel()
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setPixmap(load_logo_pixmap(max_width=96))

        title = QLabel("Batch ST-Link Flasher")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 700;")

        if len(__version_info__) >= 4:
            version_text = (
                f"Version {__version_info__[0]}.{__version_info__[1]}.{__version_info__[2]} "
                f"(build {__version_info__[3]})"
            )
        else:
            version_text = f"Version {__version__}"
        version = QLabel(version_text)
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        body = QLabel(
            "Parallel STM32 flashing via OpenOCD and ST-Link programmers.\n\n"
            "One OpenOCD process per selected adapter, with unique TCP ports "
            "and HLA serial binding when available.\n\n"
            "UI: PySide6 · Backend: OpenOCD · License: MIT"
        )
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(art)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addSpacing(4)
        layout.addWidget(body)
        layout.addStretch(1)
        layout.addWidget(buttons)
