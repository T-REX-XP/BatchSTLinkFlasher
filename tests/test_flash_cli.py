"""CLI smoke for flash module."""

from __future__ import annotations

from pathlib import Path

from batch_stlink_flasher.flash import main
from batch_stlink_flasher.flashing.models import AdapterInfo


def test_flash_dry_run(monkeypatch, tmp_path: Path, capsys) -> None:
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr(
        "batch_stlink_flasher.flash.list_adapters",
        lambda: [
            AdapterInfo(
                serial="%",
                hla_serial="",
                vid=0x0483,
                pid=0x3748,
                product="STM32 STLink",
                multi_adapter_ok=False,
            )
        ],
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.flash._resolve_openocd",
        lambda _explicit: "openocd",
    )
    assert main(["--firmware", str(fw), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "openocd" in out.lower()
    assert "hla_serial" not in out


def test_flash_dry_run_all(monkeypatch, tmp_path: Path, capsys) -> None:
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr(
        "batch_stlink_flasher.flash.list_adapters",
        lambda: [
            AdapterInfo(
                serial="A",
                hla_serial='"\\xaa"',
                vid=0x0483,
                pid=0x3748,
                multi_adapter_ok=True,
            ),
            AdapterInfo(
                serial="B",
                hla_serial='"\\xbb"',
                vid=0x0483,
                pid=0x3748,
                multi_adapter_ok=True,
            ),
        ],
    )
    monkeypatch.setattr(
        "batch_stlink_flasher.flash._resolve_openocd",
        lambda _explicit: "openocd",
    )
    assert main(["--firmware", str(fw), "--all", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert out.count("hla_serial") == 2
