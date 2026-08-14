"""Flash configuration form (compact; advanced fields collapsible)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from batch_stlink_flasher.flashing.openocd import default_bin_base_address
from batch_stlink_flasher.services.settings import AppSettings
from batch_stlink_flasher.ui.theme import decorate_button


class ConfigPanel(QWidget):
    """OpenOCD / firmware / target settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._theme_mode = "system"
        self.openocd_edit = QLineEdit()
        self.firmware_edit = QLineEdit()
        self.interface_edit = QLineEdit()
        self.target_edit = QLineEdit()
        self.scripts_edit = QLineEdit()
        self.bin_base_edit = QLineEdit()
        self.timeout_edit = QLineEdit()

        for edit in (
            self.openocd_edit,
            self.firmware_edit,
            self.interface_edit,
            self.target_edit,
            self.scripts_edit,
            self.bin_base_edit,
            self.timeout_edit,
        ):
            edit.setMinimumHeight(26)
            edit.setClearButtonEnabled(True)

        primary = QFormLayout()
        primary.setContentsMargins(0, 0, 0, 0)
        primary.setHorizontalSpacing(8)
        primary.setVerticalSpacing(4)
        primary.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        primary.addRow("OpenOCD:", self._with_browse(self.openocd_edit, self._browse_openocd))
        primary.addRow("Firmware:", self._with_browse(self.firmware_edit, self._browse_firmware))
        primary.addRow("Target cfg:", self.target_edit)

        advanced_form = QFormLayout()
        advanced_form.setContentsMargins(0, 0, 0, 0)
        advanced_form.setHorizontalSpacing(8)
        advanced_form.setVerticalSpacing(4)
        advanced_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        advanced_form.addRow("Interface cfg:", self.interface_edit)
        advanced_form.addRow(
            "Scripts (-s):",
            self._with_browse(self.scripts_edit, self._browse_scripts, dir_mode=True),
        )
        advanced_form.addRow("BIN base:", self.bin_base_edit)
        advanced_form.addRow("Timeout (s):", self.timeout_edit)

        self._advanced_body = QWidget()
        self._advanced_body.setLayout(advanced_form)
        self._advanced_body.setVisible(False)

        self._advanced_toggle = QToolButton()
        self._advanced_toggle.setObjectName("configAdvancedToggle")
        self._advanced_toggle.setText("Advanced settings")
        self._advanced_toggle.setCheckable(True)
        self._advanced_toggle.setChecked(False)
        self._advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._advanced_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self._advanced_toggle.setAutoRaise(True)
        self._advanced_toggle.toggled.connect(self._on_advanced_toggled)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(primary)
        layout.addWidget(self._advanced_toggle, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._advanced_body)

    def advanced_expanded(self) -> bool:
        return self._advanced_toggle.isChecked()

    def set_advanced_expanded(self, expanded: bool) -> None:
        self._advanced_toggle.setChecked(expanded)

    def _on_advanced_toggled(self, checked: bool) -> None:
        self._advanced_body.setVisible(checked)
        self._advanced_toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    def apply_settings(self, settings: AppSettings) -> None:
        self.openocd_edit.setText(settings.openocd_path)
        self.firmware_edit.setText(settings.last_firmware_path)
        self.interface_edit.setText(settings.interface_cfg)
        self.target_edit.setText(settings.target_cfg)
        self.scripts_edit.setText(settings.scripts_search_path)
        self.bin_base_edit.setText(settings.bin_base_address or f"0x{default_bin_base_address():X}")
        self.timeout_edit.setText(str(settings.job_timeout_sec))
        self._theme_mode = settings.theme_mode or "system"

    def to_settings(self) -> AppSettings:
        try:
            timeout = float(self.timeout_edit.text().strip() or "120")
        except ValueError:
            timeout = 120.0
        return AppSettings(
            openocd_path=self.openocd_edit.text().strip(),
            last_firmware_path=self.firmware_edit.text().strip(),
            interface_cfg=self.interface_edit.text().strip(),
            target_cfg=self.target_edit.text().strip(),
            scripts_search_path=self.scripts_edit.text().strip(),
            bin_base_address=self.bin_base_edit.text().strip()
            or f"0x{default_bin_base_address():X}",
            job_timeout_sec=timeout,
            theme_mode=getattr(self, "_theme_mode", "system"),
        )

    def _with_browse(self, edit: QLineEdit, handler, *, dir_mode: bool = False) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(edit, stretch=1)
        btn = QPushButton("…")
        btn.setFixedWidth(36)
        btn.setToolTip("Browse…")
        decorate_button(btn, standard=QStyle.StandardPixmap.SP_DirOpenIcon)
        btn.clicked.connect(handler)
        layout.addWidget(btn)
        row._dir_mode = dir_mode  # noqa: SLF001
        return row

    def _browse_openocd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select OpenOCD", self.openocd_edit.text())
        if path:
            self.openocd_edit.setText(path)

    def _browse_firmware(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select firmware",
            self.firmware_edit.text(),
            "Firmware (*.elf *.hex *.bin);;All files (*.*)",
        )
        if path:
            self.firmware_edit.setText(path)

    def _browse_scripts(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "OpenOCD scripts directory", self.scripts_edit.text()
        )
        if path:
            self.scripts_edit.setText(path)
