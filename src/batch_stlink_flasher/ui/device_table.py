"""Device list with selection and per-adapter status."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from batch_stlink_flasher.flashing.models import AdapterInfo, JobState

COL_CHECK = 0
COL_PRODUCT = 1
COL_SERIAL = 2
COL_USB_PORT = 3
COL_PID = 4
COL_HLA = 5
COL_STATUS = 6
COL_PROGRESS = 7
COL_NOTE = 8


def format_usb_port(adapter: AdapterInfo) -> str:
    """Human-readable USB port / hub for the device table."""
    if adapter.usb_port is None:
        return "-"
    if adapter.usb_hub is not None:
        return f"{adapter.usb_port} (hub {adapter.usb_hub})"
    return str(adapter.usb_port)


class DeviceTable(QTableWidget):
    """Checkbox table of discovered ST-Links."""

    def __init__(self, parent=None) -> None:
        super().__init__(0, 9, parent)
        self.setHorizontalHeaderLabels(
            ["", "Product", "Serial", "USB port", "PID", "HLA", "Status", "Progress", "Note"]
        )
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(COL_PRODUCT, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(COL_NOTE, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(COL_CHECK, 36)
        self.setColumnWidth(COL_SERIAL, 120)
        self.setColumnWidth(COL_USB_PORT, 100)
        self.setColumnWidth(COL_PID, 70)
        self.setColumnWidth(COL_HLA, 150)
        self.setColumnWidth(COL_STATUS, 100)
        self.setColumnWidth(COL_PROGRESS, 110)
        self._adapters: list[AdapterInfo] = []

    def set_adapters(self, adapters: list[AdapterInfo]) -> None:
        previous_selected = {a.serial for a in self.selected_adapters()}
        self._adapters = list(adapters)
        self.setRowCount(0)
        for adapter in adapters:
            row = self.rowCount()
            self.insertRow(row)

            check = QTableWidgetItem()
            check.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            checked = (
                Qt.CheckState.Checked
                if (not previous_selected or adapter.serial in previous_selected)
                else Qt.CheckState.Unchecked
            )
            check.setCheckState(checked)
            self.setItem(row, COL_CHECK, check)

            self.setItem(row, COL_PRODUCT, QTableWidgetItem(adapter.product or "ST-Link"))
            self.setItem(row, COL_SERIAL, QTableWidgetItem(adapter.serial))
            self.setItem(row, COL_USB_PORT, QTableWidgetItem(format_usb_port(adapter)))
            self.setItem(row, COL_PID, QTableWidgetItem(f"0x{adapter.pid:04X}"))
            hla = adapter.hla_serial or "(none)"
            self.setItem(row, COL_HLA, QTableWidgetItem(hla))
            self.setItem(row, COL_STATUS, QTableWidgetItem(JobState.IDLE.value))
            self.setItem(row, COL_PROGRESS, QTableWidgetItem("-"))
            note = adapter.skip_reason or (
                "HLA · parallel OK" if adapter.multi_adapter_ok else "clone · sequential"
            )
            self.setItem(row, COL_NOTE, QTableWidgetItem(note))

    def adapters(self) -> list[AdapterInfo]:
        return list(self._adapters)

    def selected_adapters(self) -> list[AdapterInfo]:
        selected: list[AdapterInfo] = []
        for row, adapter in enumerate(self._adapters):
            item = self.item(row, COL_CHECK)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selected.append(adapter)
        return selected

    def set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.rowCount()):
            item = self.item(row, COL_CHECK)
            if item is not None:
                item.setCheckState(state)

    def set_status_for_serial(self, serial: str, state: str, note: str | None = None) -> None:
        for row, adapter in enumerate(self._adapters):
            if adapter.serial != serial:
                continue
            status_item = self.item(row, COL_STATUS)
            if status_item is None:
                status_item = QTableWidgetItem()
                self.setItem(row, COL_STATUS, status_item)
            status_item.setText(state)
            status_item.setBackground(_status_color(state))
            if note is not None:
                note_item = self.item(row, COL_NOTE)
                if note_item is None:
                    note_item = QTableWidgetItem()
                    self.setItem(row, COL_NOTE, note_item)
                note_item.setText(note)
            if state in {
                JobState.SUCCEEDED.value,
                JobState.FAILED.value,
                JobState.CANCELLED.value,
                JobState.IDLE.value,
            }:
                self.set_progress_for_serial(
                    serial,
                    "100%" if state == JobState.SUCCEEDED.value else "-",
                )
            return

    def set_progress_for_serial(self, serial: str, label: str) -> None:
        for row, adapter in enumerate(self._adapters):
            if adapter.serial != serial:
                continue
            item = self.item(row, COL_PROGRESS)
            if item is None:
                item = QTableWidgetItem()
                self.setItem(row, COL_PROGRESS, item)
            item.setText(label)
            return

    def reset_statuses(self) -> None:
        for adapter in self._adapters:
            self.set_status_for_serial(
                adapter.serial,
                JobState.IDLE.value,
                adapter.skip_reason
                or ("HLA · parallel OK" if adapter.multi_adapter_ok else "clone · sequential"),
            )
            self.set_progress_for_serial(adapter.serial, "-")


def _status_color(state: str) -> QColor:
    mapping = {
        JobState.IDLE.value: QColor(0, 0, 0, 0),
        JobState.QUEUED.value: QColor(230, 230, 250),
        JobState.RUNNING.value: QColor(255, 250, 205),
        JobState.SUCCEEDED.value: QColor(198, 239, 206),
        JobState.FAILED.value: QColor(255, 199, 206),
        JobState.CANCELLED.value: QColor(220, 220, 220),
    }
    return mapping.get(state, QColor(0, 0, 0, 0))
