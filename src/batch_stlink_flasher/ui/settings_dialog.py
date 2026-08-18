"""Application settings dialog (OpenOCD tools, flash mode, appearance)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from batch_stlink_flasher.services.settings import (
    AppSettings,
    FlashMode,
    normalize_flash_mode,
)
from batch_stlink_flasher.ui.file_filters import openocd_executable_filter
from batch_stlink_flasher.ui.path_row import path_browse_row
from batch_stlink_flasher.ui.theme import ThemeMode, normalize_theme_mode, style_dialog_buttons


class SettingsDialog(QDialog):
    """Modal settings: tools / OpenOCD, flash strategy, and appearance."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setAutoFillBackground(True)

        self.openocd_edit = QLineEdit()
        self.scripts_edit = QLineEdit()
        self.timeout_edit = QLineEdit()
        self.timeout_edit.setMinimumHeight(26)
        self.timeout_edit.setClearButtonEnabled(True)

        self.flash_mode_combo = QComboBox()
        self.flash_mode_combo.addItem(
            "Auto — parallel HLA, sequential clones",
            FlashMode.AUTO.value,
        )
        self.flash_mode_combo.addItem(
            "Always sequential",
            FlashMode.SEQUENTIAL.value,
        )
        flash_hint = QLabel(
            "Clones without a unique HLA serial always flash one-at-a-time "
            "with USB isolation. Force-parallel for clones is not offered (unsafe)."
        )
        flash_hint.setWordWrap(True)
        flash_hint.setObjectName("mutedLabel")

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System default", ThemeMode.SYSTEM.value)
        self.theme_combo.addItem("Light", ThemeMode.LIGHT.value)
        self.theme_combo.addItem("Dark", ThemeMode.DARK.value)

        tools = QWidget()
        tools.setAutoFillBackground(True)
        tools_form = QFormLayout(tools)
        tools_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        tools_form.addRow("OpenOCD:", path_browse_row(self.openocd_edit, self._browse_openocd))
        tools_form.addRow(
            "Scripts (-s):",
            path_browse_row(self.scripts_edit, self._browse_scripts),
        )
        tools_form.addRow("Timeout (s):", self.timeout_edit)
        tools_form.addRow("Flash mode:", self.flash_mode_combo)
        tools_form.addRow("", flash_hint)

        appearance = QWidget()
        appearance.setAutoFillBackground(True)
        appearance_form = QFormLayout(appearance)
        appearance_form.addRow("Theme:", self.theme_combo)

        tabs = QTabWidget()
        tabs.addTab(tools, "OpenOCD")
        tabs.addTab(appearance, "Appearance")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        style_dialog_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

        self.apply_settings(settings)

    def apply_settings(self, settings: AppSettings) -> None:
        self.openocd_edit.setText(settings.openocd_path)
        self.scripts_edit.setText(settings.scripts_search_path)
        self.timeout_edit.setText(str(settings.job_timeout_sec))
        mode = normalize_flash_mode(settings.flash_mode).value
        flash_idx = self.flash_mode_combo.findData(mode)
        self.flash_mode_combo.setCurrentIndex(flash_idx if flash_idx >= 0 else 0)
        theme = normalize_theme_mode(settings.theme_mode).value
        idx = self.theme_combo.findData(theme)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def to_settings(self, base: AppSettings) -> AppSettings:
        """Return ``base`` with tool / appearance fields from this dialog."""
        try:
            timeout = float(self.timeout_edit.text().strip() or "120")
        except ValueError:
            timeout = 120.0
        theme = self.theme_combo.currentData()
        if not isinstance(theme, str):
            theme = ThemeMode.SYSTEM.value
        flash = self.flash_mode_combo.currentData()
        if not isinstance(flash, str):
            flash = FlashMode.AUTO.value
        return AppSettings(
            openocd_path=self.openocd_edit.text().strip(),
            last_firmware_path=base.last_firmware_path,
            interface_cfg=base.interface_cfg,
            target_cfg=base.target_cfg,
            scripts_search_path=self.scripts_edit.text().strip(),
            bin_base_address=base.bin_base_address,
            job_timeout_sec=timeout,
            theme_mode=normalize_theme_mode(theme).value,
            flash_mode=normalize_flash_mode(flash).value,
        )

    @staticmethod
    def _dialog_start_path(current: str) -> str:
        text = (current or "").strip()
        if not text:
            return ""
        path = Path(text)
        if path.is_file() or path.is_dir():
            return str(path)
        parent = path.parent
        if parent.is_dir():
            return str(parent)
        return text

    def _browse_openocd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OpenOCD executable",
            self._dialog_start_path(self.openocd_edit.text()),
            openocd_executable_filter(),
        )
        if path:
            self.openocd_edit.setText(path)

    def _browse_scripts(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "OpenOCD scripts directory",
            self._dialog_start_path(self.scripts_edit.text()),
        )
        if path:
            self.scripts_edit.setText(path)
