"""Application settings dialog (OpenOCD tools, timeout, appearance)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from batch_stlink_flasher.services.settings import AppSettings
from batch_stlink_flasher.ui.file_filters import OPENOCD_CFG_FILTER, openocd_executable_filter
from batch_stlink_flasher.ui.theme import ThemeMode, create_browse_button, normalize_theme_mode


class SettingsDialog(QDialog):
    """Modal settings: tools / OpenOCD and appearance."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.openocd_edit = QLineEdit()
        self.interface_edit = QLineEdit()
        self.scripts_edit = QLineEdit()
        self.timeout_edit = QLineEdit()
        for edit in (
            self.openocd_edit,
            self.interface_edit,
            self.scripts_edit,
            self.timeout_edit,
        ):
            edit.setMinimumHeight(26)
            edit.setClearButtonEnabled(True)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System default", ThemeMode.SYSTEM.value)
        self.theme_combo.addItem("Light", ThemeMode.LIGHT.value)
        self.theme_combo.addItem("Dark", ThemeMode.DARK.value)

        tools = QWidget()
        tools_form = QFormLayout(tools)
        tools_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        tools_form.addRow("OpenOCD:", self._with_browse(self.openocd_edit, self._browse_openocd))
        tools_form.addRow(
            "Interface cfg:",
            self._with_browse(self.interface_edit, self._browse_interface),
        )
        tools_form.addRow(
            "Scripts (-s):",
            self._with_browse(self.scripts_edit, self._browse_scripts, dir_mode=True),
        )
        tools_form.addRow("Timeout (s):", self.timeout_edit)

        appearance = QWidget()
        appearance_form = QFormLayout(appearance)
        appearance_form.addRow("Theme:", self.theme_combo)

        tabs = QTabWidget()
        tabs.addTab(tools, "OpenOCD")
        tabs.addTab(appearance, "Appearance")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

        self.apply_settings(settings)

    def apply_settings(self, settings: AppSettings) -> None:
        self.openocd_edit.setText(settings.openocd_path)
        self.interface_edit.setText(settings.interface_cfg)
        self.scripts_edit.setText(settings.scripts_search_path)
        self.timeout_edit.setText(str(settings.job_timeout_sec))
        mode = normalize_theme_mode(settings.theme_mode).value
        idx = self.theme_combo.findData(mode)
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
        return AppSettings(
            openocd_path=self.openocd_edit.text().strip(),
            last_firmware_path=base.last_firmware_path,
            interface_cfg=self.interface_edit.text().strip(),
            target_cfg=base.target_cfg,
            scripts_search_path=self.scripts_edit.text().strip(),
            bin_base_address=base.bin_base_address,
            job_timeout_sec=timeout,
            theme_mode=normalize_theme_mode(theme).value,
        )

    def _with_browse(self, edit: QLineEdit, handler, *, dir_mode: bool = False) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(edit, stretch=1)
        btn = create_browse_button()
        btn.clicked.connect(handler)
        layout.addWidget(btn)
        row._dir_mode = dir_mode  # noqa: SLF001
        return row

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

    def _browse_interface(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OpenOCD interface config",
            self._dialog_start_path(self.interface_edit.text()),
            OPENOCD_CFG_FILTER,
        )
        if path:
            self.interface_edit.setText(path)

    def _browse_scripts(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "OpenOCD scripts directory",
            self._dialog_start_path(self.scripts_edit.text()),
        )
        if path:
            self.scripts_edit.setText(path)
