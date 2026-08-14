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
