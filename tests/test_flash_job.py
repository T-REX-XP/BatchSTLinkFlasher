"""Unit tests for FlashJob process lifecycle."""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from batch_stlink_flasher.flashing.job import FlashJob
from batch_stlink_flasher.flashing.models import (
    AdapterInfo,
    FlashConfig,
    JobState,
    OpenOcdPorts,
)
from batch_stlink_flasher.flashing.openocd import summarize_openocd_error


def _adapter(**kwargs: object) -> AdapterInfo:
    defaults: dict[str, object] = {
        "serial": "abc",
        "hla_serial": '"\\xaa\\xbb"',
        "vid": 0x0483,
        "pid": 0x3748,
        "product": "ST-Link",
        "multi_adapter_ok": True,
    }
    defaults.update(kwargs)
    return AdapterInfo(**defaults)  # type: ignore[arg-type]


def _config(tmp_path: Path, **kwargs: object) -> FlashConfig:
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    defaults: dict[str, object] = {
        "openocd_path": Path("openocd"),
        "firmware_path": fw,
        "interface_cfg": "interface/stlink.cfg",
        "target_cfg": "target/stm32f1x.cfg",
        "job_timeout_sec": 5.0,
    }
    defaults.update(kwargs)
    return FlashConfig(**defaults)  # type: ignore[arg-type]


def _fake_popen(lines: list[str], exit_code: int = 0, hang: bool = False):
    class _Proc:
        def __init__(self) -> None:
            self.stdout = MagicMock()
            self._lines = list(lines)
            self._idx = 0
            self._exit = exit_code
            self._hang = hang
            self._killed = False

            def readline() -> str:
                if self._idx < len(self._lines):
                    line = self._lines[self._idx]
                    self._idx += 1
                    return line + "\n"
                if self._hang and not self._killed:
                    time.sleep(0.05)
                    return ""
                return ""

            self.stdout.readline.side_effect = readline

        def poll(self) -> int | None:
            if self._hang and not self._killed:
                return None
            return self._exit

        def wait(self, timeout: float | None = None) -> int:
            if self._hang and not self._killed:
                time.sleep(0.05 if timeout is None else min(timeout, 0.05))
                if not self._killed:
                    raise subprocess.TimeoutExpired(cmd="openocd", timeout=timeout or 0)
            return self._exit

        def terminate(self) -> None:
            self._killed = True
            self._exit = -15
            self._hang = False

        def kill(self) -> None:
            self._killed = True
            self._exit = -9
            self._hang = False

    return _Proc()


def test_summarize_openocd_error_prefers_error_line() -> None:
    lines = ["Info: ok", "Error: timed out while waiting for target halt", "shutdown"]
    assert "timed out" in summarize_openocd_error(lines, exit_code=1).lower()


def test_flash_job_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ports = OpenOcdPorts(gdb=3333, telnet=4444, tcl=6666)
    seen: list[str] = []

    monkeypatch.setattr(
        "batch_stlink_flasher.flashing.job.subprocess.Popen",
        lambda *a, **k: _fake_popen(["Info: flash done", "shutdown command invoked"], 0),
    )

    job = FlashJob(_adapter(), _config(tmp_path), ports=ports, on_line=seen.append)
    result = job.run()
    assert result.state == JobState.SUCCEEDED
    assert result.exit_code == 0
    assert any("flash done" in line for line in result.log_lines)
    assert "hla_serial" in " ".join(result.argv)


def test_flash_job_omits_hla_for_clone(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ports = OpenOcdPorts(gdb=3333, telnet=4444, tcl=6666)
    monkeypatch.setattr(
        "batch_stlink_flasher.flashing.job.subprocess.Popen",
        lambda *a, **k: _fake_popen(["ok"], 0),
    )
    adapter = _adapter(serial="%", hla_serial="", multi_adapter_ok=False)
    result = FlashJob(adapter, _config(tmp_path), ports=ports).run()
    assert result.state == JobState.SUCCEEDED
    assert not any(part.startswith("hla_serial") for part in result.argv)


def test_flash_job_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ports = OpenOcdPorts(gdb=3333, telnet=4444, tcl=6666)
    monkeypatch.setattr(
        "batch_stlink_flasher.flashing.job.subprocess.Popen",
        lambda *a, **k: _fake_popen(["Error: init mode failed"], 1),
    )
    result = FlashJob(_adapter(), _config(tmp_path), ports=ports).run()
    assert result.state == JobState.FAILED
    assert result.exit_code == 1
    assert result.error_summary and "init mode failed" in result.error_summary


def test_flash_job_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ports = OpenOcdPorts(gdb=3333, telnet=4444, tcl=6666)
    monkeypatch.setattr(
        "batch_stlink_flasher.flashing.job.subprocess.Popen",
        lambda *a, **k: _fake_popen([], 0, hang=True),
    )
    result = FlashJob(
        _adapter(),
        _config(tmp_path, job_timeout_sec=0.3),
        ports=ports,
    ).run()
    assert result.state == JobState.FAILED
    assert result.error_summary and "timed out" in result.error_summary


def test_flash_job_cancel(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ports = OpenOcdPorts(gdb=3333, telnet=4444, tcl=6666)
    proc = _fake_popen([], 0, hang=True)
    monkeypatch.setattr(
        "batch_stlink_flasher.flashing.job.subprocess.Popen",
        lambda *a, **k: proc,
    )
    job = FlashJob(_adapter(), _config(tmp_path, job_timeout_sec=30), ports=ports)

    def _cancel_soon() -> None:
        time.sleep(0.15)
        job.cancel()

    threading.Thread(target=_cancel_soon, daemon=True).start()
    result = job.run()
    assert result.state == JobState.CANCELLED
