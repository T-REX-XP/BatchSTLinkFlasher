"""Deeper MainWindow unit tests (offscreen)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from batch_stlink_flasher.flashing.job import FlashJobResult
from batch_stlink_flasher.flashing.models import AdapterInfo, JobState
from batch_stlink_flasher.flashing.orchestrator import AdapterJobResult, OrchestratorSummary
from batch_stlink_flasher.services.settings import AppSettings
from batch_stlink_flasher.ui.main_window import MainWindow
from batch_stlink_flasher.util.log_export import SessionLog


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def window(qapp: QApplication, monkeypatch: pytest.MonkeyPatch) -> MainWindow:
    # Avoid auto-refresh racing tests; splash owns the first scan in production.
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.DiscoveryWorker.start",
        lambda self: None,
    )
    win = MainWindow(auto_refresh=False)
    yield win
    win.close()


def test_validate_ok(window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    openocd = tmp_path / "openocd.exe"
    openocd.write_bytes(b"x")
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.resolve_openocd_path",
        lambda _v: openocd,
    )
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="%",
                hla_serial="",
                vid=0x0483,
                pid=0x3748,
                usb_path=r"USB\VID_0483&PID_3748\%",
                multi_adapter_ok=False,
            )
        ]
    )
    settings = AppSettings(
        openocd_path=str(openocd),
        last_firmware_path=str(fw),
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )
    assert window._validate(settings) is None  # noqa: SLF001


def test_validate_multi_clones_need_usb_path(window: MainWindow, tmp_path: Path, monkeypatch) -> None:
    openocd = tmp_path / "openocd.exe"
    openocd.write_bytes(b"x")
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.resolve_openocd_path",
        lambda _v: openocd,
    )
    window.device_table.set_adapters(
        [
            AdapterInfo(serial="%", hla_serial="", vid=0x0483, pid=0x3748, multi_adapter_ok=False),
            AdapterInfo(serial="%", hla_serial="", vid=0x0483, pid=0x3748, multi_adapter_ok=False),
        ]
    )
    window.device_table.set_all_checked(True)
    settings = AppSettings(
        openocd_path=str(openocd),
        last_firmware_path=str(fw),
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )
    err = window._validate(settings)  # noqa: SLF001
    assert err and "USB instance" in err


def test_validate_multi_clones_with_usb_path_ok(window: MainWindow, tmp_path: Path, monkeypatch) -> None:
    openocd = tmp_path / "openocd.exe"
    openocd.write_bytes(b"x")
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.resolve_openocd_path",
        lambda _v: openocd,
    )
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="%",
                hla_serial="",
                vid=0x0483,
                pid=0x3748,
                usb_path=r"USB\VID_0483&PID_3748\%",
                multi_adapter_ok=False,
            ),
            AdapterInfo(
                serial="5&a&0&1",
                hla_serial="",
                vid=0x0483,
                pid=0x3748,
                usb_path=r"USB\VID_0483&PID_3748\5&a&0&1",
                multi_adapter_ok=False,
            ),
        ]
    )
    window.device_table.set_all_checked(True)
    settings = AppSettings(
        openocd_path=str(openocd),
        last_firmware_path=str(fw),
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )
    assert window._validate(settings) is None  # noqa: SLF001


def test_progress_and_job_finished_handlers(window: MainWindow) -> None:
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="A",
                hla_serial='"\\xaa"',
                vid=0x0483,
                pid=0x3748,
                multi_adapter_ok=True,
            )
        ]
    )
    window._on_progress("A", "programming (20%)")  # noqa: SLF001
    window._on_flash_line("A", "hello")  # noqa: SLF001
    window._running_count = 1
    window._on_job_finished("A", JobState.SUCCEEDED.value, "")  # noqa: SLF001
    assert window._succeeded == 1  # noqa: SLF001


def test_run_finished_and_clear(window: MainWindow) -> None:
    summary = OrchestratorSummary(
        results=[
            AdapterJobResult(
                AdapterInfo(serial="A", hla_serial="x", vid=0x0483, pid=0x3748),
                FlashJobResult(JobState.SUCCEEDED, 0, 0.1),
            )
        ]
    )
    window._on_run_finished(summary)  # noqa: SLF001
    window._clear_log()  # noqa: SLF001
    assert isinstance(window._session, SessionLog)  # noqa: SLF001


def test_start_and_cancel_flash(window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    openocd = tmp_path / "openocd.exe"
    openocd.write_bytes(b"x")
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.resolve_openocd_path",
        lambda _v: openocd,
    )
    settings = AppSettings(
        openocd_path=str(openocd),
        last_firmware_path=str(fw),
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )
    window._settings = settings
    window.config_panel.apply_settings(settings)
    window._update_tools_summary()  # noqa: SLF001
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="%",
                hla_serial="",
                vid=0x0483,
                pid=0x3748,
                usb_path=r"USB\VID_0483&PID_3748\%",
                multi_adapter_ok=False,
            )
        ]
    )

    class _Worker:
        def __init__(self, *a, **k):
            self.line_received = MagicMock()
            self.progress_updated = MagicMock()
            self.job_finished = MagicMock()
            self.run_finished = MagicMock()
            self.failed = MagicMock()
            self._running = True

        def start(self):
            return None

        def isRunning(self):
            return self._running

        def cancel(self):
            self._running = False

    monkeypatch.setattr("batch_stlink_flasher.ui.main_window.FlashWorker", _Worker)
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.save_settings",
        lambda _s: None,
    )
    window.start_flash()
    assert window.cancel_btn.isEnabled()
    window.cancel_flash()


def test_export_log_text_only(window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "session.log"
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(out), "Text (*.log *.txt)"),
    )
    window._session.append("line")  # noqa: SLF001
    window.export_log()
    assert out.exists()


def test_identify_requires_exactly_one(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import MagicMock

    box = MagicMock()
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.QMessageBox.information",
        box,
    )
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="A",
                hla_serial="A",
                vid=0x0483,
                pid=0x3748,
                usb_path=r"USB\VID_0483&PID_3748\A",
                usb_port=1,
                multi_adapter_ok=True,
            )
        ]
    )
    window.device_table.set_all_checked(False)
    window.identify_selected()
    assert box.called


def test_identify_requires_usb_path(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    warn = MagicMock()
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.QMessageBox.warning",
        warn,
    )
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="A",
                hla_serial="A",
                vid=0x0483,
                pid=0x3748,
                usb_path=None,
                multi_adapter_ok=True,
            )
        ]
    )
    window.device_table.set_all_checked(True)
    window.identify_selected()
    assert warn.called


def test_identify_starts_worker(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    class _IdWorker:
        def __init__(self, *a, **k):
            self.finished_ok = MagicMock()
            self.failed = MagicMock()
            self.finished = MagicMock()
            self._running = True

        def start(self):
            return None

        def isRunning(self):
            return self._running

    monkeypatch.setattr("batch_stlink_flasher.ui.main_window.IdentifyWorker", _IdWorker)
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.QMessageBox.warning",
        MagicMock(),
    )
    window.device_table.set_adapters(
        [
            AdapterInfo(
                serial="A",
                hla_serial="A",
                vid=0x0483,
                pid=0x3748,
                usb_path=r"USB\VID_0483&PID_3748\A",
                usb_port=2,
                multi_adapter_ok=True,
            )
        ]
    )
    window.device_table.set_all_checked(True)
    window.identify_selected()
    assert window._identify is not None  # noqa: SLF001
    assert not window.identify_btn.isEnabled()
    window._on_identify_ok("A")  # noqa: SLF001
    window._on_identify_failed("nope")  # noqa: SLF001
    window._on_identify_finished()  # noqa: SLF001
    assert window.identify_btn.isEnabled()


def test_close_while_flashing_asks_confirmation(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtGui import QCloseEvent
    from PySide6.QtWidgets import QMessageBox

    class _Worker:
        def __init__(self):
            self._running = True
            self.cancelled = False

        def isRunning(self):
            return self._running

        def cancel(self):
            self.cancelled = True
            self._running = False

        def wait(self, _ms=None):
            return True

    worker = _Worker()
    window._flash = worker  # noqa: SLF001
    answers = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]

    def _question(*_a, **_k):
        return answers.pop(0)

    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.QMessageBox.question",
        _question,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.save_settings",
        lambda _s: None,
    )

    denied = QCloseEvent()
    window.closeEvent(denied)
    assert denied.isAccepted() is False
    assert worker.cancelled is False

    accepted = QCloseEvent()
    window.closeEvent(accepted)
    assert accepted.isAccepted() is True
    assert worker.cancelled is True
    window._flash = None  # noqa: SLF001 — allow fixture teardown close()
