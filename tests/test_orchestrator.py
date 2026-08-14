"""Unit tests for FlashOrchestrator."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from batch_stlink_flasher.flashing.job import FlashJobResult
from batch_stlink_flasher.flashing.models import AdapterInfo, FlashConfig, JobState
from batch_stlink_flasher.flashing.orchestrator import FlashOrchestrator


def _adapter(
    serial: str,
    *,
    ok: bool = True,
    hla: str | None = None,
    usb_path: str | None = None,
) -> AdapterInfo:
    return AdapterInfo(
        serial=serial,
        hla_serial=hla if hla is not None else (f'"{serial}"' if ok else ""),
        vid=0x0483,
        pid=0x3748,
        product="ST-Link",
        usb_path=usb_path or (rf"USB\VID_0483&PID_3748\{serial}"),
        multi_adapter_ok=ok,
        skip_reason=None if ok else "placeholder",
    )


def _config(tmp_path: Path) -> FlashConfig:
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    return FlashConfig(
        openocd_path=Path("openocd"),
        firmware_path=fw,
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
        job_timeout_sec=5.0,
    )


def _patch_job_run(monkeypatch: pytest.MonkeyPatch, outcomes: dict[str, JobState]) -> None:
    def _run(self: object) -> FlashJobResult:
        from batch_stlink_flasher.flashing.job import FlashJob

        assert isinstance(self, FlashJob)
        serial = self.adapter.serial
        state = outcomes.get(serial, JobState.SUCCEEDED)
        for _ in range(10):
            if self._cancel.is_set():  # noqa: SLF001
                self._state = JobState.CANCELLED  # noqa: SLF001
                return FlashJobResult(
                    state=JobState.CANCELLED, exit_code=None, elapsed_sec=0.1
                )
            time.sleep(0.02)
        if state == JobState.FAILED:
            self._state = JobState.FAILED  # noqa: SLF001
            return FlashJobResult(
                state=JobState.FAILED,
                exit_code=1,
                elapsed_sec=0.1,
                error_summary=f"failed {serial}",
            )
        self._state = JobState.SUCCEEDED  # noqa: SLF001
        return FlashJobResult(state=JobState.SUCCEEDED, exit_code=0, elapsed_sec=0.1)

    monkeypatch.setattr("batch_stlink_flasher.flashing.job.FlashJob.run", _run)


def test_orchestrator_runs_parallel_and_isolates_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_job_run(
        monkeypatch,
        {"A": JobState.SUCCEEDED, "B": JobState.FAILED, "C": JobState.SUCCEEDED},
    )
    adapters = [_adapter("A"), _adapter("B"), _adapter("C")]
    done: list[str] = []
    orch = FlashOrchestrator(
        adapters,
        _config(tmp_path),
        on_job_done=lambda a, r: done.append(f"{a.serial}:{r.state.value}"),
    )
    summary = orch.run()
    assert summary.total == 3
    assert summary.succeeded == 2
    assert summary.failed == 1
    assert sorted(done) == ["A:succeeded", "B:failed", "C:succeeded"]


def test_orchestrator_mixed_hla_and_clone_sequential(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """HLA probes parallel; clones run sequentially with isolation."""
    _patch_job_run(
        monkeypatch,
        {"GOOD": JobState.SUCCEEDED, "%": JobState.SUCCEEDED},
    )
    disabled: list[str] = []
    enabled: list[str] = []

    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.disable_device",
        lambda iid: disabled.append(iid) or True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.enable_device",
        lambda iid: enabled.append(iid) or True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.sys",
        type("S", (), {"platform": "win32"})(),
    )

    adapters = [
        _adapter("GOOD", ok=True, usb_path=r"USB\VID_0483&PID_3748\GOOD"),
        _adapter("%", ok=False, hla="", usb_path=r"USB\VID_0483&PID_3748\%"),
    ]
    summary = FlashOrchestrator(adapters, _config(tmp_path)).run()
    assert summary.succeeded == 2
    assert summary.failed == 0
    assert r"USB\VID_0483&PID_3748\GOOD" in disabled
    assert r"USB\VID_0483&PID_3748\GOOD" in enabled


def test_orchestrator_force_sequential_hla(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """force_sequential runs HLA jobs one-at-a-time (no sibling disable for HLA)."""
    started: list[str] = []
    lock = threading.Lock()
    active = 0
    max_active = 0

    def _run(self: object) -> FlashJobResult:
        from batch_stlink_flasher.flashing.job import FlashJob

        assert isinstance(self, FlashJob)
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
            started.append(self.adapter.serial)
        time.sleep(0.05)
        with lock:
            active -= 1
        self._state = JobState.SUCCEEDED  # noqa: SLF001
        return FlashJobResult(state=JobState.SUCCEEDED, exit_code=0, elapsed_sec=0.05)

    monkeypatch.setattr("batch_stlink_flasher.flashing.job.FlashJob.run", _run)
    adapters = [_adapter("A"), _adapter("B")]
    summary = FlashOrchestrator(
        adapters, _config(tmp_path), force_sequential=True
    ).run()
    assert summary.succeeded == 2
    assert max_active == 1
    assert started == ["A", "B"]


def test_orchestrator_clone_isolation_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_job_run(monkeypatch, {"%": JobState.SUCCEEDED})
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.disable_device",
        lambda _iid: False,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.sys",
        type("S", (), {"platform": "win32"})(),
    )
    adapters = [
        _adapter("%", ok=False, hla="", usb_path=r"USB\VID_0483&PID_3748\%"),
        _adapter(
            "5&abc&0&1",
            ok=False,
            hla="",
            usb_path=r"USB\VID_0483&PID_3748\5&abc&0&1",
        ),
    ]
    summary = FlashOrchestrator(adapters, _config(tmp_path)).run()
    assert summary.failed >= 1
    assert any("disable" in (r.result.error_summary or "").lower() for r in summary.results)


def test_orchestrator_cancel_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_job_run(monkeypatch, {"A": JobState.SUCCEEDED, "B": JobState.SUCCEEDED})
    orch = FlashOrchestrator([_adapter("A"), _adapter("B")], _config(tmp_path))

    def _cancel() -> None:
        for _ in range(50):
            if orch.is_running:
                time.sleep(0.05)
                orch.cancel_all()
                return
            time.sleep(0.01)

    threading.Thread(target=_cancel, daemon=True).start()
    summary = orch.run()
    assert summary.cancelled + summary.succeeded + summary.failed == 2
    assert summary.cancelled >= 1


def test_orchestrator_clone_missing_usb_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_job_run(monkeypatch, {})
    adapters = [
        AdapterInfo(
            serial="%",
            hla_serial="",
            vid=0x0483,
            pid=0x3748,
            usb_path=None,
            multi_adapter_ok=False,
        )
    ]
    summary = FlashOrchestrator(adapters, _config(tmp_path)).run()
    assert summary.failed == 1
    assert "instance id" in (summary.results[0].result.error_summary or "").lower()


def test_orchestrator_rejects_concurrent_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    started = threading.Event()
    release = threading.Event()

    def _run(self: object) -> FlashJobResult:
        started.set()
        release.wait(timeout=2)
        return FlashJobResult(state=JobState.SUCCEEDED, exit_code=0, elapsed_sec=0.1)

    monkeypatch.setattr("batch_stlink_flasher.flashing.job.FlashJob.run", _run)
    orch = FlashOrchestrator([_adapter("A")], _config(tmp_path))

    def _background() -> None:
        orch.run()

    t = threading.Thread(target=_background, daemon=True)
    t.start()
    assert started.wait(timeout=2)
    with pytest.raises(RuntimeError, match="already in progress"):
        orch.run()
    release.set()
    t.join(timeout=2)
