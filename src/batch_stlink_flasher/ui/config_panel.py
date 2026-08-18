"""Flash job configuration form (firmware / target — tools live in Settings)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QSizePolicy,
    QWidget,
)

from batch_stlink_flasher.flashing.openocd import default_bin_base_address
from batch_stlink_flasher.services.settings import AppSettings
from batch_stlink_flasher.ui.config_scanner import (
    WELL_KNOWN_TARGETS,
    get_default_target_config,
    infer_scripts_dir_from_openocd,
    looks_like_scripts_dir,
    scan_scripts_directory,
)
from batch_stlink_flasher.ui.file_filters import FIRMWARE_FILTER
from batch_stlink_flasher.ui.path_row import path_browse_row


class ConfigPanel(QWidget):
    """Per-run flash fields kept on the main window."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.firmware_edit = QLineEdit()
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.target_combo.setMinimumHeight(26)
        self.target_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        self.target_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.target_combo.setMinimumContentsLength(20)
        self.bin_base_edit = QLineEdit()
        self.bin_base_edit.setMinimumHeight(26)
        self.bin_base_edit.setClearButtonEnabled(True)

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(4)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.addRow("Firmware:", path_browse_row(self.firmware_edit, self._browse_firmware))
        form.addRow("Target cfg:", self.target_combo)
        form.addRow("BIN base:", self.bin_base_edit)

    def apply_settings(self, settings: AppSettings) -> None:
        self.firmware_edit.setText(settings.last_firmware_path)
        self.bin_base_edit.setText(settings.bin_base_address or f"0x{default_bin_base_address():X}")
        self._refresh_target_options(
            settings.target_cfg,
            settings.scripts_search_path,
            settings.openocd_path,
        )

    def merge_into(self, base: AppSettings) -> AppSettings:
        """Return ``base`` with job fields taken from this panel."""
        target_cfg = self.target_combo.currentText().strip()
        if not target_cfg:
            target_cfg = get_default_target_config()
        return AppSettings(
            openocd_path=base.openocd_path,
            last_firmware_path=self.firmware_edit.text().strip(),
            interface_cfg=base.interface_cfg,
            target_cfg=target_cfg,
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

    def _refresh_target_options(self, current_value: str, scripts_path: str = "", openocd_path: str = "") -> None:
        """Refresh the target combo box options from scripts directory."""
        # If scripts_path is empty, doesn't exist, or doesn't contain an
        # interface/ or target/ subdirectory, try to infer from the OpenOCD exe.
        if not scripts_path or not looks_like_scripts_dir(scripts_path):
            inferred = infer_scripts_dir_from_openocd(openocd_path)
            if inferred is not None:
                scripts_path = str(inferred)

        _, target_configs = scan_scripts_directory(scripts_path)

        # Merge well-known defaults so the dropdown is never empty.
        merged: list[str] = []
        seen: set[str] = set()
        for cfg in list(WELL_KNOWN_TARGETS) + target_configs:
            if cfg not in seen:
                merged.append(cfg)
                seen.add(cfg)

        self.target_combo.clear()
        for cfg in merged:
            self.target_combo.addItem(cfg, cfg)

        if current_value:
            idx = self.target_combo.findData(current_value)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)
            else:
                self.target_combo.setEditText(current_value)
        elif merged:
            self.target_combo.setCurrentIndex(0)
