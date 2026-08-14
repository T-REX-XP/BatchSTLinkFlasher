"""Flash job configuration form (firmware / target — tools live in Settings)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QSizePolicy,
    QWidget,
)

from batch_stlink_flasher.flashing.openocd import default_bin_base_address
from batch_stlink_flasher.services.settings import AppSettings
from batch_stlink_flasher.ui.file_filters import FIRMWARE_FILTER, OPENOCD_CFG_FILTER
from batch_stlink_flasher.ui.path_row import path_browse_row


class ConfigPanel(QWidget):
    """Per-run flash fields kept on the main window."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.firmware_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.bin_base_edit = QLineEdit()
        self.bin_base_edit.setMinimumHeight(26)
        self.bin_base_edit.setClearButtonEnabled(True)

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(4)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Firmware:", path_browse_row(self.firmware_edit, self._browse_firmware))
        form.addRow("Target cfg:", path_browse_row(self.target_edit, self._browse_target))
        form.addRow("BIN base:", self.bin_base_edit)

    def apply_settings(self, settings: AppSettings) -> None:
        self.firmware_edit.setText(settings.last_firmware_path)
        self.target_edit.setText(settings.target_cfg)
        self.bin_base_edit.setText(settings.bin_base_address or f"0x{default_bin_base_address():X}")

    def merge_into(self, base: AppSettings) -> AppSettings:
        """Return ``base`` with job fields taken from this panel."""
        return AppSettings(
            openocd_path=base.openocd_path,
            last_firmware_path=self.firmware_edit.text().strip(),
            interface_cfg=base.interface_cfg,
            target_cfg=self.target_edit.text().strip(),
            scripts_search_path=base.scripts_search_path,
            bin_base_address=self.bin_base_edit.text().strip()
            or f"0x{default_bin_base_address():X}",
            job_timeout_sec=base.job_timeout_sec,
            theme_mode=base.theme_mode,
            flash_mode=base.flash_mode,
        )

    def to_settings(self, base: AppSettings | None = None) -> AppSettings:
        return self.merge_into(base or AppSettings())

    @staticmethod
    def _dialog_start_path(current: str) -> str:
        text = (current or "").strip()
        if not text:
            return ""
        path = Path(text)
        if path.is_file():
            return str(path)
        if path.is_dir():
            return str(path)
        parent = path.parent
        if parent.is_dir():
            return str(parent)
        return text

    def _browse_firmware(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select firmware",
            self._dialog_start_path(self.firmware_edit.text()),
            FIRMWARE_FILTER,
        )
        if path:
            self.firmware_edit.setText(path)

    def _browse_target(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OpenOCD target/board config",
            self._dialog_start_path(self.target_edit.text()),
            OPENOCD_CFG_FILTER,
        )
        if path:
            self.target_edit.setText(path)
