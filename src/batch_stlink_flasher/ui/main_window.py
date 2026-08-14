"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from batch_stlink_flasher import __version__
from batch_stlink_flasher.flashing.models import FlashConfig, JobState
from batch_stlink_flasher.flashing.orchestrator import OrchestratorSummary
from batch_stlink_flasher.services.settings import (
    load_settings,
    resolve_openocd_path,
    save_settings,
)
from batch_stlink_flasher.ui.about_dialog import AboutDialog
from batch_stlink_flasher.ui.config_panel import ConfigPanel
from batch_stlink_flasher.ui.device_table import DeviceTable
from batch_stlink_flasher.ui.log_view import LogView
from batch_stlink_flasher.ui.theme import (
    ThemeMode,
    apply_app_theme,
    decorate_button,
    load_app_icon,
    normalize_theme_mode,
)
from batch_stlink_flasher.ui.workers import DiscoveryWorker, FlashWorker
from batch_stlink_flasher.util.log_export import SessionLog, export_log_json, export_log_text


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        initial_adapters: list | None = None,
        initial_scan_error: str | None = None,
        auto_refresh: bool | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(f"Batch ST-Link Flasher {__version__}")
        icon = load_app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(1100, 720)

        self._discovery: DiscoveryWorker | None = None
        self._flash: FlashWorker | None = None
        self._running_count = 0
        self._succeeded = 0
        self._failed = 0
        self._cancelled = 0
        self._session = SessionLog()

        self.device_table = DeviceTable()
        self.device_table.setAlternatingRowColors(True)
        self.config_panel = ConfigPanel()
        self.log_view = LogView()
        self.summary_label = QLabel("Idle")
        self.summary_label.setObjectName("summaryLabel")

        self.refresh_btn = QPushButton("Refresh devices")
        self.select_all_btn = QPushButton("Select all")
        self.select_none_btn = QPushButton("Select none")
        self.flash_btn = QPushButton("Flash")
        self.cancel_btn = QPushButton("Cancel")
        self.clear_log_btn = QPushButton("Clear log")
        self.export_log_btn = QPushButton("Export log")
        self.cancel_btn.setEnabled(False)

        decorate_button(self.refresh_btn, standard=QStyle.StandardPixmap.SP_BrowserReload)
        decorate_button(self.select_all_btn, standard=QStyle.StandardPixmap.SP_DialogYesButton)
        decorate_button(self.select_none_btn, standard=QStyle.StandardPixmap.SP_DialogNoButton)
        decorate_button(
            self.flash_btn,
            standard=QStyle.StandardPixmap.SP_DialogApplyButton,
            role="primary",
        )
        decorate_button(
            self.cancel_btn,
            standard=QStyle.StandardPixmap.SP_DialogCancelButton,
            role="danger",
        )
        decorate_button(self.clear_log_btn, standard=QStyle.StandardPixmap.SP_DialogResetButton)
        decorate_button(self.export_log_btn, standard=QStyle.StandardPixmap.SP_DialogSaveButton)

        top_btns = QHBoxLayout()
        top_btns.setSpacing(8)
        top_btns.addWidget(self.refresh_btn)
        top_btns.addWidget(self.select_all_btn)
        top_btns.addWidget(self.select_none_btn)
        top_btns.addStretch(1)
        top_btns.addWidget(self.export_log_btn)
        top_btns.addWidget(self.clear_log_btn)
        top_btns.addWidget(self.cancel_btn)
        top_btns.addWidget(self.flash_btn)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 8)
        left_layout.setSpacing(10)
        left_layout.addLayout(top_btns)
        left_layout.addWidget(self.device_table, stretch=2)
        left_layout.addWidget(self.config_panel, stretch=0)
        left_layout.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(left)
        splitter.addWidget(self.log_view)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(splitter)
        self.setCentralWidget(container)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Ready - Refresh devices to scan for ST-Links")

        self._build_menu()
        self._connect_signals()

        initial_settings = load_settings()
        self.config_panel.apply_settings(initial_settings)
        self._theme_mode = normalize_theme_mode(initial_settings.theme_mode)
        self._sync_theme_actions()
        app = QApplication.instance()
        if app is not None:
            app.styleHints().colorSchemeChanged.connect(self._on_system_color_scheme_changed)

        # Splash may hand off a completed scan; otherwise refresh on startup.
        if auto_refresh is None:
            auto_refresh = initial_adapters is None and not initial_scan_error

        if initial_adapters is not None:
            self._on_discovery_ok(list(initial_adapters))
            if initial_scan_error:
                self.statusBar().showMessage(f"Startup scan warning: {initial_scan_error}")
            elif not initial_adapters:
                self.statusBar().showMessage("Startup scan: no ST-Link adapters found")
            else:
                self.statusBar().showMessage(
                    f"Startup scan: found {len(initial_adapters)} adapter(s)"
                )
        elif initial_scan_error:
            self._on_discovery_failed(initial_scan_error)
        elif auto_refresh:
            self.refresh_devices()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        refresh_action = QAction("Refresh devices", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self.refresh_devices)
        file_menu.addAction(refresh_action)

        flash_action = QAction("Flash", self)
        flash_action.setShortcut(QKeySequence("Ctrl+Return"))
        flash_action.triggered.connect(self.start_flash)
        file_menu.addAction(flash_action)

        cancel_action = QAction("Cancel", self)
        cancel_action.setShortcut(QKeySequence("Esc"))
        cancel_action.triggered.connect(self.cancel_flash)
        file_menu.addAction(cancel_action)

        export_action = QAction("Export log...", self)
        export_action.setShortcut(QKeySequence("Ctrl+S"))
        export_action.triggered.connect(self.export_log)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = self.menuBar().addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions: dict[ThemeMode, QAction] = {}
        for mode, label in (
            (ThemeMode.SYSTEM, "System default"),
            (ThemeMode.LIGHT, "Light"),
            (ThemeMode.DARK, "Dark"),
        ):
            action = QAction(label, self)
            action.setCheckable(True)
            action.setData(mode.value)
            action.triggered.connect(lambda checked=False, m=mode: self.set_theme_mode(m))
            self._theme_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[mode] = action

        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About", self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)
        shortcuts = QAction("Shortcuts", self)
        shortcuts.triggered.connect(self._shortcuts)
        help_menu.addAction(shortcuts)

    def set_theme_mode(self, mode: ThemeMode | str) -> None:
        """Apply and persist appearance preference."""
        resolved = normalize_theme_mode(mode)
        self._theme_mode = resolved
        self.config_panel._theme_mode = resolved.value  # noqa: SLF001
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_app_theme(app, resolved)
        self._sync_theme_actions()
        # Persist immediately so restart keeps the choice.
        settings = self.config_panel.to_settings()
        settings.theme_mode = resolved.value
        save_settings(settings)

    def _sync_theme_actions(self) -> None:
        action = self._theme_actions.get(self._theme_mode)
        if action is not None:
            action.setChecked(True)

    def _on_system_color_scheme_changed(self, _scheme) -> None:
        if self._theme_mode is ThemeMode.SYSTEM:
            app = QApplication.instance()
            if isinstance(app, QApplication):
                apply_app_theme(app, ThemeMode.SYSTEM)

    def _connect_signals(self) -> None:
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.select_all_btn.clicked.connect(lambda: self.device_table.set_all_checked(True))
        self.select_none_btn.clicked.connect(lambda: self.device_table.set_all_checked(False))
        self.flash_btn.clicked.connect(self.start_flash)
        self.cancel_btn.clicked.connect(self.cancel_flash)
        self.clear_log_btn.clicked.connect(self._clear_log)
        self.export_log_btn.clicked.connect(self.export_log)

    def refresh_devices(self) -> None:
        if self._flash is not None and self._flash.isRunning():
            self.statusBar().showMessage("Cannot refresh while flashing")
            return
        if self._discovery is not None and self._discovery.isRunning():
            return

        self.refresh_btn.setEnabled(False)
        self.statusBar().showMessage("Scanning for ST-Links...")
        worker = DiscoveryWorker()
        worker.finished_ok.connect(self._on_discovery_ok)
        worker.failed.connect(self._on_discovery_failed)
        worker.finished.connect(lambda: self.refresh_btn.setEnabled(True))
        self._discovery = worker
        worker.start()

    def _on_discovery_ok(self, adapters: list) -> None:
        self.device_table.set_adapters(adapters)
        self.statusBar().showMessage(f"Found {len(adapters)} adapter(s)")
        self._update_summary_idle()

    def _on_discovery_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"Discovery failed: {message}")
        QMessageBox.warning(self, "Discovery failed", message)

    def start_flash(self) -> None:
        if self._flash is not None and self._flash.isRunning():
            QMessageBox.information(self, "Busy", "A flash run is already in progress.")
            return

        settings = self.config_panel.to_settings()
        save_settings(settings)
        error = self._validate(settings)
        if error:
            QMessageBox.warning(self, "Cannot start", error)
            return

        adapters = self.device_table.selected_adapters()
        config = self._build_flash_config(settings)
        assert config is not None

        self.log_view.append_line("--- flash start ---")
        self._session.append("--- flash start ---")
        self.device_table.reset_statuses()
        for adapter in adapters:
            self.device_table.set_status_for_serial(adapter.serial, JobState.QUEUED.value)

        self._running_count = len(adapters)
        self._succeeded = 0
        self._failed = 0
        self._cancelled = 0
        self._update_summary_counts()

        from batch_stlink_flasher.flashing.orchestrator import can_bind_hla

        n_hla = sum(1 for a in adapters if can_bind_hla(a))
        n_clone = len(adapters) - n_hla
        mode_bits: list[str] = []
        if n_hla:
            mode_bits.append(f"{n_hla} parallel (HLA)")
        if n_clone:
            mode_bits.append(f"{n_clone} sequential (clone isolate)")
        mode = " + ".join(mode_bits) if mode_bits else "flash"

        self.flash_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.refresh_btn.setEnabled(False)

        worker = FlashWorker(
            adapters,
            config,
            known_adapters=self.device_table.adapters(),
        )
        worker.line_received.connect(self._on_flash_line)
        worker.progress_updated.connect(self._on_progress)
        worker.job_finished.connect(self._on_job_finished)
        worker.run_finished.connect(self._on_run_finished)
        worker.failed.connect(self._on_flash_failed)
        self._flash = worker
        worker.start()
        self.statusBar().showMessage(f"Flashing {len(adapters)} device(s): {mode}")
        self.log_view.append_line(f"--- mode: {mode} ---")
        self._session.append(f"--- mode: {mode} ---")

    def cancel_flash(self) -> None:
        if self._flash is not None and self._flash.isRunning():
            self._flash.cancel()
            self.statusBar().showMessage("Cancel requested...")
            self.log_view.append_line("--- cancel requested ---")
            self._session.append("--- cancel requested ---")

    def _on_flash_line(self, serial: str, line: str) -> None:
        self.device_table.set_status_for_serial(serial, JobState.RUNNING.value)
        prefixed = f"[{serial}] {line}"
        self.log_view.append_line(prefixed)
        self._session.append(prefixed)

    def _on_progress(self, serial: str, label: str) -> None:
        self.device_table.set_progress_for_serial(serial, label)

    def _on_job_finished(self, serial: str, state: str, error: str) -> None:
        note = error if error else state
        self.device_table.set_status_for_serial(serial, state, note)
        self._session.add_result(serial, state, error)
        if state == JobState.SUCCEEDED.value:
            self._succeeded += 1
        elif state == JobState.CANCELLED.value:
            self._cancelled += 1
        else:
            self._failed += 1
        self._running_count = max(0, self._running_count - 1)
        self._update_summary_counts()

    def _on_run_finished(self, summary: object) -> None:
        assert isinstance(summary, OrchestratorSummary)
        done = (
            f"--- done: {summary.succeeded} ok / {summary.failed} failed / "
            f"{summary.cancelled} cancelled ---"
        )
        self.log_view.append_line(done)
        self._session.append(done)
        self.statusBar().showMessage(
            f"Finished: {summary.succeeded} succeeded, {summary.failed} failed, "
            f"{summary.cancelled} cancelled"
        )
        self._set_idle_controls()
        self._update_summary_counts(
            succeeded=summary.succeeded,
            failed=summary.failed,
            cancelled=summary.cancelled,
            running=0,
        )

    def _on_flash_failed(self, message: str) -> None:
        self.log_view.append_line(f"ERROR: {message}")
        self._session.append(f"ERROR: {message}")
        QMessageBox.critical(self, "Flash error", message)
        self._set_idle_controls()
        self.statusBar().showMessage(f"Flash error: {message}")

    def _clear_log(self) -> None:
        self.log_view.clear_log()
        self._session = SessionLog()

    def export_log(self) -> None:
        path_str, selected = QFileDialog.getSaveFileName(
            self,
            "Export session log",
            "flash-session.log",
            "Text (*.log *.txt);;JSON (*.json)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            if path.suffix.lower() == ".json" or "JSON" in selected:
                if path.suffix.lower() != ".json":
                    path = path.with_suffix(".json")
                export_log_json(path, self._session)
            else:
                if path.suffix.lower() not in {".log", ".txt"}:
                    path = path.with_suffix(".log")
                export_log_text(path, self._session)
        except OSError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Log exported to {path}")

    def _set_idle_controls(self) -> None:
        self.flash_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)

    def _validate(self, settings) -> str | None:
        openocd = resolve_openocd_path(settings.openocd_path)
        if openocd is None:
            return "OpenOCD not found. Set a valid path or add it to PATH."

        firmware = Path(settings.last_firmware_path)
        if not settings.last_firmware_path or not firmware.is_file():
            return "Firmware file not found."

        suffix = firmware.suffix.lower()
        if suffix not in {".elf", ".hex", ".bin"}:
            return "Firmware must be .elf, .hex, or .bin."

        if not settings.interface_cfg:
            return "Interface config is required (e.g. interface/stlink.cfg)."
        if not settings.target_cfg:
            return "Target config is required (e.g. target/stm32f1x.cfg)."

        if suffix == ".bin":
            try:
                int(settings.bin_base_address, 0)
            except ValueError:
                return "BIN base address is invalid (example: 0x08000000)."

        try:
            if float(settings.job_timeout_sec) <= 0:
                return "Timeout must be positive."
        except (TypeError, ValueError):
            return "Timeout must be a number."

        selected = self.device_table.selected_adapters()
        if not selected:
            return "Select at least one adapter."

        from batch_stlink_flasher.flashing.orchestrator import can_bind_hla

        unbound = [a for a in selected if not can_bind_hla(a)]
        if unbound and any(not (a.usb_path or "").strip() for a in unbound):
            return (
                "Selected clone/unbound adapters need a USB instance path "
                "for isolation. Refresh devices and try again."
            )
        return None

    def _build_flash_config(self, settings) -> FlashConfig | None:
        openocd = resolve_openocd_path(settings.openocd_path)
        if openocd is None:
            return None
        firmware = Path(settings.last_firmware_path)
        bin_base = None
        if firmware.suffix.lower() == ".bin":
            bin_base = int(settings.bin_base_address, 0)
        scripts = Path(settings.scripts_search_path) if settings.scripts_search_path else None
        return FlashConfig(
            openocd_path=openocd,
            firmware_path=firmware,
            interface_cfg=settings.interface_cfg,
            target_cfg=settings.target_cfg,
            bin_base_address=bin_base,
            scripts_search_path=scripts,
            job_timeout_sec=float(settings.job_timeout_sec),
        )

    def _update_summary_idle(self) -> None:
        n = len(self.device_table.adapters())
        self.summary_label.setText(f"Devices: {n}  |  Idle")

    def _update_summary_counts(
        self,
        *,
        succeeded: int | None = None,
        failed: int | None = None,
        cancelled: int | None = None,
        running: int | None = None,
    ) -> None:
        s = self._succeeded if succeeded is None else succeeded
        f = self._failed if failed is None else failed
        c = self._cancelled if cancelled is None else cancelled
        r = self._running_count if running is None else running
        self.summary_label.setText(
            f"Running: {r}  |  Succeeded: {s}  |  Failed: {f}  |  Cancelled: {c}"
        )

    def _about(self) -> None:
        AboutDialog(self).exec()

    def _shortcuts(self) -> None:
        QMessageBox.information(
            self,
            "Shortcuts",
            "Ctrl+Return - Start flash\n"
            "Esc - Cancel\n"
            "Ctrl+S - Export log\n"
            "F5 / Refresh - Rescan devices\n"
            "View → Theme - System / Light / Dark",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        save_settings(self.config_panel.to_settings())
        if self._flash is not None and self._flash.isRunning():
            self._flash.cancel()
            self._flash.wait(3000)
        event.accept()
