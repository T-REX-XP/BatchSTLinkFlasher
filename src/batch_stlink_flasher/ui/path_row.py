"""Shared path row: line edit + identical browse (``…``) button."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from batch_stlink_flasher.ui.theme import create_browse_button


def path_browse_row(edit: QLineEdit, on_browse: Callable[[], None]) -> QWidget:
    """
    Build a single path field row used by the main window and Settings.

    Ensures the ``…`` button is the same control (size, chrome) everywhere.
    """
    edit.setMinimumHeight(26)
    edit.setClearButtonEnabled(True)

    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(edit, stretch=1)

    btn = create_browse_button(row, height=edit.minimumHeight())
    btn.clicked.connect(on_browse)
    layout.addWidget(btn, stretch=0)
    return row
