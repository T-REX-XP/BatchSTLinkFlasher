"""Tests for st-info --probe parsing and adapter mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_stlink_flasher.services.device_service import adapters_from_stinfo_stdout, list_adapters
from batch_stlink_flasher.services.stinfo_parser import parse_stinfo_probe

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_one_probe_modern_hla() -> None:
    probes = parse_stinfo_probe(_load("stinfo_probe_one.txt"))
    assert len(probes) == 1
    assert probes[0].serial.startswith("30303341")
    assert "\\x30\\x30\\x33\\x41" in probes[0].hla_serial
    assert probes[0].descr.startswith("L0xx")


def test_parse_two_probes_legacy_openocd_key() -> None:
    probes = parse_stinfo_probe(_load("stinfo_probe_two_openocd.txt"))
    assert len(probes) == 2
    assert probes[0].serial == "543f6e06723f495507372267"
    assert probes[0].hla_serial.startswith('"\\x54')
    assert probes[1].descr == "F07x device"


def test_parse_wrapped_hla_serial() -> None:
    probes = parse_stinfo_probe(_load("stinfo_probe_wrapped_hla.txt"))
    assert len(probes) == 1
    hla = probes[0].hla_serial
    assert hla.startswith('"\\x30')
    assert hla.endswith('"')
    assert "\\" not in hla.replace("\\x", "")  # no leftover line-continuation backslash


def test_parse_none() -> None:
    assert parse_stinfo_probe(_load("stinfo_probe_none.txt")) == []


def test_adapters_from_stinfo_stdout_normalizes_hla() -> None:
    adapters = adapters_from_stinfo_stdout(_load("stinfo_probe_two_openocd.txt"))
    assert len(adapters) == 2
    assert adapters[0].hla_serial.startswith('"\\x54')
    assert adapters[0].vid == 0x0483
    assert adapters[1].product == "F07x device"


def test_list_adapters_uses_stinfo_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = _load("stinfo_probe_one.txt")

    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service._resolve_stinfo",
        lambda _path=None: "st-info",
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.run_stinfo_probe",
        lambda *_a, **_k: stdout,
    )

    called = {"pyusb": False, "pnp": False}

    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_adapters_pyusb",
        lambda: called.__setitem__("pyusb", True) or [],
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_adapters_windows_pnp",
        lambda: called.__setitem__("pnp", True) or [],
    )

    adapters = list_adapters()
    assert len(adapters) == 1
    assert called["pyusb"] is False
    assert called["pnp"] is False


def test_list_adapters_uses_windows_pnp_before_pyusb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service._resolve_stinfo",
        lambda _path=None: None,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.sys.platform",
        "win32",
    )

    from batch_stlink_flasher.flashing.models import AdapterInfo

    fake = [
        AdapterInfo(
            serial="%",
            hla_serial="",
            vid=0x0483,
            pid=0x3748,
            product="STM32 STLink",
            multi_adapter_ok=False,
            skip_reason="placeholder",
        )
    ]
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_adapters_windows_pnp",
        lambda: fake,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_adapters_pyusb",
        lambda: (_ for _ in ()).throw(AssertionError("pyusb should not run")),
    )

    assert list_adapters() == fake


def test_list_adapters_falls_back_to_pyusb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service._resolve_stinfo",
        lambda _path=None: None,
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_adapters_windows_pnp",
        lambda: [],
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.sys.platform",
        "win32",
    )

    from batch_stlink_flasher.flashing.models import AdapterInfo

    fake = [
        AdapterInfo(
            serial="aa",
            hla_serial='"\\xaa"',
            vid=0x0483,
            pid=0x3748,
            product="ST-Link/V2",
        )
    ]
    monkeypatch.setattr(
        "batch_stlink_flasher.services.device_service.list_adapters_pyusb",
        lambda: fake,
    )

    adapters = list_adapters()
    assert adapters == fake
