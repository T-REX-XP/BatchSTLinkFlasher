"""Tests for ST-Link Identify LED helper."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.services.identify import blink_adapter_led
from batch_stlink_flasher.services.windows_device_control import DeviceIsolationError


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _adapter(*, path: str | None = r"USB\VID_0483&PID_3748\%") -> AdapterInfo:
    return AdapterInfo(
        serial="%",
        hla_serial="",
        vid=0x0483,
        pid=0x3748,
        usb_path=path,
        usb_port=1,
        multi_adapter_ok=False,
    )


def test_blink_requires_usb_path() -> None:
    with pytest.raises(DeviceIsolationError, match="instance id"):
        blink_adapter_led(_adapter(path=None))


def test_blink_pulses_disable_enable(monkeypatch) -> None:
    ops: list[str] = []
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.disable_device",
        lambda iid: ops.append(f"off:{iid}") or True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.enable_device",
        lambda iid: ops.append(f"on:{iid}") or True,
    )
    monkeypatch.setattr("batch_stlink_flasher.services.identify.time.sleep", lambda _s: None)

    blink_adapter_led(_adapter(), pulses=2, off_sec=0.01, on_sec=0.01)
    assert ops == [
        r"off:USB\VID_0483&PID_3748\%",
        r"on:USB\VID_0483&PID_3748\%",
        r"off:USB\VID_0483&PID_3748\%",
        r"on:USB\VID_0483&PID_3748\%",
    ]


def test_blink_raises_when_disable_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.disable_device",
        lambda _iid: False,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.enable_device",
        lambda _iid: True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.is_access_denied_status",
        lambda: False,
    )
    monkeypatch.setattr("batch_stlink_flasher.services.identify.time.sleep", lambda _s: None)
    with pytest.raises(DeviceIsolationError, match="could not disable"):
        blink_adapter_led(_adapter(), pulses=1, allow_elevate=False)


def test_blink_elevates_on_access_denied(monkeypatch) -> None:
    calls = {"n": 0}

    def _disable(_iid: str) -> bool:
        calls["n"] += 1
        return False

    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.disable_device",
        _disable,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.enable_device",
        lambda _iid: True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.is_access_denied_status",
        lambda: True,
    )
    monkeypatch.setattr("batch_stlink_flasher.services.identify.time.sleep", lambda _s: None)
    monkeypatch.setattr(
        "batch_stlink_flasher.util.win_elevate.is_user_an_admin",
        lambda: False,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.util.win_elevate.run_elevated",
        lambda *_a, **_k: 0,
    )
    blink_adapter_led(_adapter(), pulses=1, allow_elevate=True)
    assert calls["n"] == 1


def test_blink_raises_when_enable_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.disable_device",
        lambda _iid: True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.enable_device",
        lambda _iid: False,
    )
    monkeypatch.setattr("batch_stlink_flasher.services.identify.time.sleep", lambda _s: None)
    with pytest.raises(DeviceIsolationError, match="could not re-enable"):
        blink_adapter_led(_adapter(), pulses=1)


def test_blink_rejects_zero_pulses() -> None:
    with pytest.raises(ValueError, match="pulses"):
        blink_adapter_led(_adapter(), pulses=0)


def test_identify_worker_ok(qapp, monkeypatch) -> None:
    from batch_stlink_flasher.ui.workers import IdentifyWorker

    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.blink_adapter_led",
        lambda *_a, **_k: None,
    )
    worker = IdentifyWorker(_adapter(), pulses=1)
    seen: list[str] = []
    worker.finished_ok.connect(seen.append)
    worker.run()
    assert seen == ["%"]


def test_identify_worker_failed(qapp, monkeypatch) -> None:
    from batch_stlink_flasher.ui.workers import IdentifyWorker

    monkeypatch.setattr(
        "batch_stlink_flasher.services.identify.blink_adapter_led",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    worker = IdentifyWorker(_adapter(), pulses=1)
    errs: list[str] = []
    worker.failed.connect(errs.append)
    worker.run()
    assert errs == ["boom"]
