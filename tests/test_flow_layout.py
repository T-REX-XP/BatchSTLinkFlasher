"""Tests for FlowLayout wrapping behavior."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from batch_stlink_flasher.ui.flow_layout import FlowLayout


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_flow_layout_wraps(qapp: QApplication) -> None:
    host = QWidget()
    layout = FlowLayout(host, margin=0, spacing=4)
    buttons = [QPushButton(f"B{i}") for i in range(6)]
    for btn in buttons:
        btn.setFixedSize(80, 28)
        layout.addWidget(btn)

    narrow_h = layout.heightForWidth(120)
    wide_h = layout.heightForWidth(600)
    assert narrow_h > wide_h
    assert narrow_h >= 28 * 2
    assert layout.count() == 6
    assert layout.itemAt(0) is not None
    assert layout.itemAt(99) is None
    assert layout.expandingDirections() == Qt.Orientation(0)
    assert layout.hasHeightForWidth() is True
    assert layout.spacing() == 4
    taken = layout.takeAt(0)
    assert taken is not None
    assert layout.count() == 5
    assert layout.takeAt(99) is None

    host.resize(200, max(narrow_h, 40) + 8)
    host.show()
    qapp.processEvents()
    layout.setGeometry(host.rect())
    assert layout.minimumSize().width() >= 80
    assert layout.sizeHint().height() >= 28

    buttons[1].hide()
    h_hidden = layout.heightForWidth(120)
    assert h_hidden >= 28
