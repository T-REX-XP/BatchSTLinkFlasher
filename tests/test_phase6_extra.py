"""Additional coverage tests for discovery, flash CLI, and workers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from batch_stlink_flasher.flash import main as flash_main
from batch_stlink_flasher.flashing.job import FlashJobResult
from batch_stlink_flasher.flashing.models import AdapterInfo, FlashConfig, JobState
from batch_stlink_flasher.flashing.orchestrator import AdapterJobResult, OrchestratorSummary
from batch_stlink_flasher.services import device_service, windows_pnp
from batch_stlink_flasher.services.windows_pnp import WindowsUsbDevice
from batch_stlink_flasher.util.logging_setup import configure_logging


def _adapter(serial: str = "A", *, ok: bool = True) -> AdapterInfo:
    return AdapterInfo(
        serial=serial,
        hla_serial=f'"{serial}"' if ok else "",
        vid=0x0483,
        pid=0x3748,
        product="ST-Link",
        multi_adapter_ok=ok,
    )


def test_configure_logging_twice() -> None:
    configure_logging()
    configure_logging()


def test_windows_pnp_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        windows_pnp,
        "_enumerate_stlink_registry",
        lambda: [
            {
                "Name": "STM32 STLink",
                "Manufacturer": "ST",
                "DeviceID": r"USB\VID_0483&PID_3748\ABCDEF",
            }
        ],
    )
    monkeypatch.setattr(windows_pnp.sys, "platform", "win32")
    devices = windows_pnp.list_stlink_pnp_devices()
    assert len(devices) == 1
    assert devices[0].pid == 0x3748
    assert devices[0].usb_serial == "ABCDEF"


def test_windows_pnp_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(windows_pnp.sys, "platform", "linux")
    assert windows_pnp.list_stlink_pnp_devices() == []


def test_run_stinfo_probe_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        args=["st-info", "--probe"],
        returncode=1,
        stdout="",
        stderr="boom",
    )
    monkeypatch.setattr(device_service.subprocess, "run", lambda *a, **k: completed)
    with pytest.raises(subprocess.CalledProcessError):
        device_service.run_stinfo_probe("st-info")


def test_list_adapters_stinfo_then_return(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device_service, "_resolve_stinfo", lambda _=None: "st-info")
    monkeypatch.setattr(
        device_service,
        "run_stinfo_probe",
        lambda *_a, **_k: (Path("tests/fixtures/stinfo_probe_one.txt").read_text(encoding="utf-8")),
    )
    adapters = device_service.list_adapters(allow_windows_pnp=False, allow_pyusb_fallback=False)
    assert len(adapters) == 1


def test_list_adapters_pyusb_backend_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Usb:
        class core:
            @staticmethod
            def find(**_kwargs):
                raise RuntimeError("No backend available")

        class util:
            pass

    import sys

    monkeypatch.setitem(sys.modules, "usb", _Usb())
    monkeypatch.setitem(sys.modules, "usb.core", _Usb.core)
    monkeypatch.setitem(sys.modules, "usb.util", _Usb.util)
    assert device_service.list_adapters_pyusb() == []


def test_flash_missing_openocd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fw = tmp_path / "a.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr("batch_stlink_flasher.flash._resolve_openocd", lambda _x: None)
    assert flash_main(["--firmware", str(fw)]) == 2


def test_flash_missing_firmware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("batch_stlink_flasher.flash._resolve_openocd", lambda _x: "openocd")
    assert flash_main(["--firmware", "missing.elf"]) == 2


def test_flash_no_adapters(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fw = tmp_path / "a.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr("batch_stlink_flasher.flash._resolve_openocd", lambda _x: "openocd")
    monkeypatch.setattr("batch_stlink_flasher.flash.list_adapters", lambda: [])
    assert flash_main(["--firmware", str(fw)]) == 1


def test_flash_all_with_orchestrator(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fw = tmp_path / "a.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr("batch_stlink_flasher.flash._resolve_openocd", lambda _x: "openocd")
    monkeypatch.setattr(
        "batch_stlink_flasher.flash.list_adapters",
        lambda: [_adapter("A"), _adapter("B")],
    )

    class _Orch:
        def __init__(self, *a, **k):
            pass

        def run(self):
            return OrchestratorSummary(
                results=[
                    AdapterJobResult(
                        _adapter("A"),
                        FlashJobResult(JobState.SUCCEEDED, 0, 0.1),
                    ),
                    AdapterJobResult(
                        _adapter("B"),
                        FlashJobResult(JobState.FAILED, 1, 0.1, error_summary="boom"),
                    ),
                ]
            )

    monkeypatch.setattr("batch_stlink_flasher.flash.FlashOrchestrator", _Orch)
    assert flash_main(["--firmware", str(fw), "--all"]) == 1


def test_flash_single_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fw = tmp_path / "a.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr("batch_stlink_flasher.flash._resolve_openocd", lambda _x: "openocd")
    monkeypatch.setattr("batch_stlink_flasher.flash.list_adapters", lambda: [_adapter("%", ok=False)])

    class _Job:
        def __init__(self, *a, **k):
            pass

        def run(self):
            return FlashJobResult(JobState.SUCCEEDED, 0, 0.2)

    monkeypatch.setattr("batch_stlink_flasher.flash.FlashJob", _Job)
    assert flash_main(["--firmware", str(fw)]) == 0


def test_discovery_worker(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    from batch_stlink_flasher.ui.workers import DiscoveryWorker

    monkeypatch.setattr(
        "batch_stlink_flasher.ui.workers.list_adapters",
        lambda: [_adapter("X")],
    )
    worker = DiscoveryWorker()
    seen: list = []
    worker.finished_ok.connect(lambda adapters: seen.extend(adapters))
    worker.run()  # call directly (not start) for deterministic test
    assert len(seen) == 1


def test_flash_worker(qapp, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from batch_stlink_flasher.ui.workers import FlashWorker

    fw = tmp_path / "a.elf"
    fw.write_bytes(b"\x00")
    cfg = FlashConfig(
        openocd_path=Path("openocd"),
        firmware_path=fw,
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )

    class _Orch:
        def __init__(
            self,
            adapters,
            config,
            on_line=None,
            on_job_done=None,
            known_adapters=None,
            force_sequential=False,
        ):
            self._on_line = on_line
            self._on_done = on_job_done

        def run(self):
            adapter = _adapter("A")
            if self._on_line:
                self._on_line(adapter, "** Programming Started **")
            result = FlashJobResult(JobState.SUCCEEDED, 0, 0.1)
            if self._on_done:
                self._on_done(adapter, result)
            return OrchestratorSummary(results=[AdapterJobResult(adapter, result)])

        def cancel_all(self):
            pass

    monkeypatch.setattr("batch_stlink_flasher.ui.workers.FlashOrchestrator", _Orch)
    worker = FlashWorker([_adapter("A")], cfg, force_sequential=True)
    progress: list[str] = []
    worker.progress_updated.connect(lambda _s, label: progress.append(label))
    finished: list = []
    worker.run_finished.connect(lambda summary: finished.append(summary))
    worker.run()
    assert finished
    assert any("programming" in p for p in progress)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
