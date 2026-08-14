"""Tests for Windows PnP instance-id parsing."""

from __future__ import annotations

from batch_stlink_flasher.services.windows_pnp import (
    is_usable_usb_serial,
    parse_usb_instance_id,
)
from batch_stlink_flasher.services.device_service import list_adapters_windows_pnp
from batch_stlink_flasher.services.windows_pnp import WindowsUsbDevice


def test_parse_usb_instance_id() -> None:
    assert parse_usb_instance_id(r"USB\VID_0483&PID_3748\66FF55") == (
        0x0483,
        0x3748,
        "66FF55",
    )


def test_parse_clone_placeholder_serial() -> None:
    assert parse_usb_instance_id(r"USB\VID_0483&PID_3748\%") == (0x0483, 0x3748, "%")


def test_unusable_serials() -> None:
    assert is_usable_usb_serial("%") is False
    assert is_usable_usb_serial("") is False
    assert is_usable_usb_serial("66FF55") is True


def test_list_adapters_windows_pnp_maps_placeholder(monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_stlink_pnp_devices",
        lambda: [
            WindowsUsbDevice(
                name="STM32 STLink",
                manufacturer="STMicroelectronics",
                instance_id=r"USB\VID_0483&PID_3748\%",
                vid=0x0483,
                pid=0x3748,
                usb_serial="%",
            )
        ],
    )
    adapters = list_adapters_windows_pnp()
    assert len(adapters) == 1
    assert adapters[0].pid == 0x3748
    assert adapters[0].hla_serial == ""
    assert adapters[0].multi_adapter_ok is False
    assert adapters[0].skip_reason


def test_clean_reg_string() -> None:
    from batch_stlink_flasher.services import windows_pnp

    assert windows_pnp._clean_reg_string("@oem12.inf,%desc%;STM32 STLink") == "STM32 STLink"  # noqa: SLF001
    assert windows_pnp._clean_reg_string("plain") == "plain"


def test_enumerate_stlink_registry(monkeypatch) -> None:
    """Simulate HKLM USB enum tree with one present ST-Link."""
    from batch_stlink_flasher.services import windows_pnp

    class FakeKey:
        def __init__(self, children=None, values=None):
            self.children = children or []
            self.values = values or {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    tree = {
        windows_pnp._USB_ENUM_ROOT: FakeKey(children=["VID_0483&PID_3748", "VID_1234&PID_0001"]),
        rf"{windows_pnp._USB_ENUM_ROOT}\VID_0483&PID_3748": FakeKey(children=["66FF55", "OLD"]),
        rf"{windows_pnp._USB_ENUM_ROOT}\VID_0483&PID_3748\66FF55": FakeKey(
            values={
                "FriendlyName": "STM32 STLink",
                "Mfg": "@oem.inf,%mfg%;STMicroelectronics",
                "DeviceDesc": "desc;STM32 STLink",
            },
        ),
        rf"{windows_pnp._USB_ENUM_ROOT}\VID_0483&PID_3748\OLD": FakeKey(),
        rf"{windows_pnp._USB_ENUM_ROOT}\VID_1234&PID_0001": FakeKey(children=[]),
    }

    def open_key(_hive, path):
        if path not in tree:
            raise OSError("missing")
        return tree[path]

    def enum_key(key, index):
        if index >= len(key.children):
            raise OSError("done")
        return key.children[index]

    def query_value(key, name):
        if name not in key.values:
            raise OSError("missing value")
        return key.values[name], 1

    monkeypatch.setattr(windows_pnp.winreg, "OpenKey", open_key)
    monkeypatch.setattr(windows_pnp.winreg, "EnumKey", enum_key)
    monkeypatch.setattr(windows_pnp.winreg, "QueryValueEx", query_value)
    monkeypatch.setattr(
        windows_pnp,
        "_device_present",
        lambda device_id: device_id.endswith(r"\66FF55"),
    )

    rows = windows_pnp._enumerate_stlink_registry()  # noqa: SLF001
    assert len(rows) == 1
    assert rows[0]["DeviceID"].endswith(r"\66FF55")
    assert rows[0]["Name"] == "STM32 STLink"
    assert rows[0]["Manufacturer"] == "STMicroelectronics"


def test_list_stlink_skips_composite_instance_ids(monkeypatch) -> None:
    from batch_stlink_flasher.services import windows_pnp

    monkeypatch.setattr(windows_pnp.sys, "platform", "win32")
    monkeypatch.setattr(
        windows_pnp,
        "_enumerate_stlink_registry",
        lambda: [
            {
                "Name": "ST-Link",
                "Manufacturer": "ST",
                "DeviceID": r"USB\VID_0483&PID_3748\%",
            },
            {
                "Name": "Composite",
                "Manufacturer": "ST",
                "DeviceID": r"USB\VID_0483&PID_3748\5&28bd6581&0&6",
            },
        ],
    )
    devices = windows_pnp.list_stlink_pnp_devices()
    assert len(devices) == 1
    assert devices[0].usb_serial == "%"


def test_hidden_subprocess_kwargs_has_startupinfo(monkeypatch) -> None:
    from batch_stlink_flasher.util import win_process

    monkeypatch.setattr(win_process.sys, "platform", "win32")
    kwargs = win_process.hidden_subprocess_kwargs()
    assert "startupinfo" in kwargs
    assert kwargs["startupinfo"].dwFlags & win_process.subprocess.STARTF_USESHOWWINDOW
