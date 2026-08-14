"""Tests for Windows ST-Link device isolation helpers."""

from __future__ import annotations

import pytest

from batch_stlink_flasher.services.windows_device_control import (
    DeviceIsolationError,
    isolated_usb_device,
)


def test_isolated_no_siblings_is_noop(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.sys",
        type("S", (), {"platform": "win32"})(),
    )
    with isolated_usb_device(r"USB\VID_0483&PID_3748\%", []):
        pass


def test_isolated_requires_target_id() -> None:
    with pytest.raises(DeviceIsolationError, match="no USB instance"):
        with isolated_usb_device("", [r"USB\B"]):
            pass


def test_isolated_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.sys",
        type("S", (), {"platform": "linux"})(),
    )
    with pytest.raises(DeviceIsolationError, match="Windows"):
        with isolated_usb_device(r"USB\A", [r"USB\B"]):
            pass


def test_disable_enable_locate_mocked(monkeypatch) -> None:
    from batch_stlink_flasher.services import windows_device_control as wdc

    monkeypatch.setattr(wdc.sys, "platform", "win32")

    class _Cfg:
        def CM_Locate_DevNodeW(self, _ref, _iid, _flags):
            return wdc._CR_SUCCESS

        def CM_Disable_DevNode(self, _dev, _flags):
            return wdc._CR_SUCCESS

        def CM_Enable_DevNode(self, _dev, _flags):
            return wdc._CR_SUCCESS

    class _Windll:
        def __init__(self, *_a, **_k):
            pass

    # DWORD byref assignment: patch locate to return a fake inst
    monkeypatch.setattr(wdc, "locate_dev_inst", lambda _iid: 42)
    monkeypatch.setattr(
        wdc.ctypes,
        "WinDLL",
        lambda *_a, **_k: type("D", (), {
            "CM_Disable_DevNode": staticmethod(lambda *_a, **_k: wdc._CR_SUCCESS),
            "CM_Enable_DevNode": staticmethod(lambda *_a, **_k: wdc._CR_SUCCESS),
        })(),
    )
    assert wdc.disable_device(r"USB\X") is True
    assert wdc.enable_device(r"USB\X") is True


def test_disable_returns_false_when_missing(monkeypatch) -> None:
    from batch_stlink_flasher.services import windows_device_control as wdc

    monkeypatch.setattr(wdc.sys, "platform", "win32")
    monkeypatch.setattr(wdc, "locate_dev_inst", lambda _iid: None)
    assert wdc.disable_device(r"USB\X") is False
    assert wdc.enable_device(r"USB\X") is False


def test_locate_non_windows(monkeypatch) -> None:
    from batch_stlink_flasher.services import windows_device_control as wdc

    monkeypatch.setattr(wdc.sys, "platform", "linux")
    assert wdc.locate_dev_inst(r"USB\X") is None
    assert wdc.disable_device(r"USB\X") is False


def test_isolated_disables_and_reenables(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.sys",
        type("S", (), {"platform": "win32"})(),
    )
    ops: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.disable_device",
        lambda iid: ops.append(("off", iid)) or True,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.enable_device",
        lambda iid: ops.append(("on", iid)) or True,
    )

    target = r"USB\VID_0483&PID_3748\%"
    sibling = r"USB\VID_0483&PID_3748\5&x&0&1"
    with isolated_usb_device(target, [target, sibling]):
        assert ops == [("off", sibling)]
    assert ops == [("off", sibling), ("on", sibling)]


def test_isolated_raises_when_disable_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.sys",
        type("S", (), {"platform": "win32"})(),
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.windows_device_control.disable_device",
        lambda _iid: False,
    )
    with pytest.raises(DeviceIsolationError, match="could not disable"):
        with isolated_usb_device(r"USB\A", [r"USB\B"]):
            pass
