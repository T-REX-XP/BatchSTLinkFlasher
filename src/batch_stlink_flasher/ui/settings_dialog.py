"""Application settings dialog (OpenOCD tools, flash mode, appearance)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from batch_stlink_flasher.services.settings import (
    AppSettings,
    FlashMode,
    normalize_flash_mode,
)
from batch_stlink_flasher.ui.config_scanner import (
    WELL_KNOWN_INTERFACES,
    get_default_interface_config,
    infer_scripts_dir_from_openocd,
    looks_like_scripts_dir,
    scan_scripts_directory,
)
from batch_stlink_flasher.ui.file_filters import OPENOCD_CFG_FILTER, openocd_executable_filter
from batch_stlink_flasher.ui.path_row import path_browse_row
from batch_stlink_flasher.ui.theme import ThemeMode, normalize_theme_mode


class SettingsDialog(QDialog):
    """Modal settings: tools / OpenOCD, flash strategy, and appearance."""

    scripts_path_changed = Signal()

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(520)
        self.setAutoFillBackground(True)

        self.openocd_edit = QLineEdit()
        self.interface_combo = QComboBox()
        self.interface_combo.setEditable(True)
        self.interface_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.interface_combo.setMinimumHeight(26)
        self.interface_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed,
        )
        self.interface_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.interface_combo.setMinimumContentsLength(20)
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
        tools_form.addRow("Interface cfg:", self.interface_combo)
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
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

        self.scripts_edit.editingFinished.connect(self._on_scripts_path_changed)

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
        self._refresh_interface_options(settings.interface_cfg)

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
        interface_cfg = self.interface_combo.currentText().strip()
        if not interface_cfg:
            interface_cfg = get_default_interface_config()
        return AppSettings(
            openocd_path=self.openocd_edit.text().strip(),
            last_firmware_path=base.last_firmware_path,
            interface_cfg=interface_cfg,
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
            self._on_scripts_path_changed()

    def _on_scripts_path_changed(self) -> None:
        """Refresh interface options when scripts path changes."""
        current_value = self.interface_combo.currentText().strip()
        self._refresh_interface_options(current_value)
        self.scripts_path_changed.emit()

    def _refresh_interface_options(self, current_value: str) -> None:
        """Refresh the interface combo box options from scripts directory."""
        scripts_path = self.scripts_edit.text().strip()

        # If scripts_path is empty, doesn't exist, or doesn't contain an
        # interface/ subdirectory, try to infer from the OpenOCD exe.
        if not scripts_path or not looks_like_scripts_dir(scripts_path):
            inferred = infer_scripts_dir_from_openocd(self.openocd_edit.text().strip())
            if inferred is not None:
                scripts_path = str(inferred)

        interface_configs, _ = scan_scripts_directory(scripts_path)

        # Merge well-known defaults so the dropdown is never empty.
        merged: list[str] = []
        seen: set[str] = set()
        for cfg in list(WELL_KNOWN_INTERFACES) + interface_configs:
            if cfg not in seen:
                merged.append(cfg)
                seen.add(cfg)

        self.interface_combo.clear()
        for cfg in merged:
            self.interface_combo.addItem(cfg, cfg)

        if current_value:
            idx = self.interface_combo.findData(current_value)
            if idx >= 0:
                self.interface_combo.setCurrentIndex(idx)
            else:
                self.interface_combo.setEditText(current_value)
        elif merged:
            self.interface_combo.setCurrentIndex(0)
