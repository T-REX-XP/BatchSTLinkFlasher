"""CLI smoke for discover module."""

from __future__ import annotations

from batch_stlink_flasher.discover import main
from batch_stlink_flasher.flashing.models import AdapterInfo


def test_discover_main_prints_adapters(monkeypatch, capsys) -> None:
    fake = [
        AdapterInfo(
            serial="abc",
            hla_serial='"\\xab\\xcd"',
            vid=0x0483,
            pid=0x3748,
            product="ST-Link/V2",
            manufacturer="ST",
            usb_path="1:2",
        )
    ]
    monkeypatch.setattr(
        "batch_stlink_flasher.discover.list_adapters",
        lambda **_kwargs: fake,
    )
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "Found 1 adapter(s)" in out
    assert "hla_serial=" in out


def test_discover_main_none(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.discover.list_adapters",
        lambda **_kwargs: [],
    )
    assert main([]) == 1
    assert "No ST-Link" in capsys.readouterr().out
