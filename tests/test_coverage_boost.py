"""More coverage for device_service / windows_pnp / flash helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from batch_stlink_flasher.flashing.models import FlashConfig
from batch_stlink_flasher.flashing.openocd import summarize_openocd_error
from batch_stlink_flasher.services import device_service, windows_pnp
from batch_stlink_flasher.services.settings import resolve_openocd_path
from batch_stlink_flasher.services.windows_pnp import WindowsUsbDevice
from batch_stlink_flasher.util.hla_serial import normalize_hla_serial


def test_resolve_openocd_path_missing() -> None:
    assert resolve_openocd_path("") is None
    assert resolve_openocd_path("definitely-not-openocd-xyz") is None


def test_resolve_openocd_path_file(tmp_path: Path) -> None:
    exe = tmp_path / "openocd.exe"
    exe.write_bytes(b"x")
    assert resolve_openocd_path(str(exe)) == exe


def test_summarize_empty_log() -> None:
    assert "exited" in summarize_openocd_error([], exit_code=7)


def test_normalize_printable_and_raw() -> None:
    assert normalize_hla_serial(hla_serial="SERIALOK") == "SERIALOK"
    assert normalize_hla_serial(raw_usb_serial="AB").startswith('"\\x')


def test_list_adapters_windows_pnp_real_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        device_service,
        "list_stlink_pnp_devices",
        lambda: [
            WindowsUsbDevice(
                name="STM32 STLink",
                manufacturer="ST",
                instance_id=r"USB\VID_0483&PID_3748\66FF55AA",
                vid=0x0483,
                pid=0x3748,
                usb_serial="66FF55AA",
            )
        ],
    )
    adapters = device_service.list_adapters_windows_pnp()
    assert len(adapters) == 1
    assert adapters[0].multi_adapter_ok is True
    assert adapters[0].hla_serial


def test_windows_pnp_query(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = SimpleNamespace(returncode=0, stdout='{"Name":"X","DeviceID":"USB\\\\VID_0483&PID_3748\\\\ABC"}', stderr="")
    monkeypatch.setattr(windows_pnp.subprocess, "run", lambda *a, **k: completed)
    monkeypatch.setattr(windows_pnp.sys, "platform", "win32")
    raw = windows_pnp._query_pnp_json()  # noqa: SLF001
    assert "VID_0483" in raw


def test_windows_pnp_query_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = SimpleNamespace(returncode=1, stdout="", stderr="err")
    monkeypatch.setattr(windows_pnp.subprocess, "run", lambda *a, **k: completed)
    assert windows_pnp._query_pnp_json() == ""  # noqa: SLF001


def test_list_adapters_pyusb_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class Dev:
        idProduct = 0x3748
        iSerialNumber = 1
        iProduct = 2
        iManufacturer = 3
        bus = 1
        address = 2

    class Core:
        @staticmethod
        def find(**_kwargs):
            return [Dev()]

    class Util:
        @staticmethod
        def get_string(dev, index):
            return {1: "AB", 2: "ST-Link/V2", 3: "ST"}.get(index, "")

    import sys
    from types import ModuleType

    usb = ModuleType("usb")
    usb.core = Core()  # type: ignore[attr-defined]
    usb.util = Util()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "usb", usb)
    monkeypatch.setitem(sys.modules, "usb.core", usb.core)
    monkeypatch.setitem(sys.modules, "usb.util", usb.util)

    adapters = device_service.list_adapters_pyusb()
    assert len(adapters) == 1
    assert adapters[0].product == "ST-Link/V2"


def test_flash_config_validate_edges(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FlashConfig(
            openocd_path=Path("openocd"),
            firmware_path=tmp_path / "a.elf",
            interface_cfg="",
            target_cfg="target/stm32f1x.cfg",
        ).validate()
    with pytest.raises(ValueError):
        FlashConfig(
            openocd_path=Path("openocd"),
            firmware_path=tmp_path / "a.elf",
            interface_cfg="interface/stlink.cfg",
            target_cfg="",
        ).validate()
    with pytest.raises(ValueError):
        FlashConfig(
            openocd_path=Path("openocd"),
            firmware_path=tmp_path / "a.bin",
            interface_cfg="interface/stlink.cfg",
            target_cfg="target/stm32f1x.cfg",
            bin_base_address=-1,
        ).validate()
    with pytest.raises(ValueError):
        FlashConfig(
            openocd_path=Path("openocd"),
            firmware_path=tmp_path / "a.elf",
            interface_cfg="interface/stlink.cfg",
            target_cfg="target/stm32f1x.cfg",
            job_timeout_sec=0,
        ).validate()


def test_small_utils_edges() -> None:
    from batch_stlink_flasher.util.ports import allocate_openocd_ports_batch
    from batch_stlink_flasher.util.progress import parse_openocd_progress

    with pytest.raises(ValueError):
        allocate_openocd_ports_batch(0)
    assert parse_openocd_progress("   ") is None


def test_log_view_device_line() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from batch_stlink_flasher.ui.log_view import LogView

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    view = LogView()
    view.append_device_line("A", "hello")
    assert "hello" in view.toPlainText()


def test_orchestrator_cancel_adapter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from batch_stlink_flasher.flashing.orchestrator import FlashOrchestrator
    from batch_stlink_flasher.flashing.models import AdapterInfo, FlashConfig
    import threading
    import time

    fw = tmp_path / "a.elf"
    fw.write_bytes(b"\x00")
    cfg = FlashConfig(
        openocd_path=Path("openocd"),
        firmware_path=fw,
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
        job_timeout_sec=5,
    )
    adapter = AdapterInfo(
        serial="A",
        hla_serial='"\\xaa"',
        vid=0x0483,
        pid=0x3748,
        multi_adapter_ok=True,
    )

    def _run(self):
        for _ in range(20):
            if self._cancel.is_set():
                from batch_stlink_flasher.flashing.job import FlashJobResult
                from batch_stlink_flasher.flashing.models import JobState

                return FlashJobResult(JobState.CANCELLED, None, 0.1)
            time.sleep(0.02)
        from batch_stlink_flasher.flashing.job import FlashJobResult
        from batch_stlink_flasher.flashing.models import JobState

        return FlashJobResult(JobState.SUCCEEDED, 0, 0.1)

    monkeypatch.setattr("batch_stlink_flasher.flashing.job.FlashJob.run", _run)
    orch = FlashOrchestrator([adapter], cfg)

    def _cancel():
        for _ in range(50):
            if orch.is_running:
                assert orch.cancel_adapter("A") is True
                return
            time.sleep(0.01)

    threading.Thread(target=_cancel, daemon=True).start()
    summary = orch.run()
    assert summary.cancelled >= 1
