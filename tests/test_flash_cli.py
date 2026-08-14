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


def test_flash_select_errors_and_bin_base(monkeypatch, tmp_path: Path) -> None:
    from batch_stlink_flasher import flash as flash_mod

    fw = tmp_path / "app.bin"
    fw.write_bytes(b"\x00")
    adapters = [
        AdapterInfo(
            serial="A",
            hla_serial='"\\xaa"',
            vid=0x0483,
            pid=0x3748,
            multi_adapter_ok=True,
            skip_reason="note",
        )
    ]
    monkeypatch.setattr(flash_mod, "list_adapters", lambda: adapters)
    monkeypatch.setattr(flash_mod, "_resolve_openocd", lambda _e: "openocd")

    # Conflicting selection modes
    assert main(["--firmware", str(fw), "--all", "--adapters", "1", "--dry-run"]) == 1
    # Missing firmware (not dry-run)
    assert main(["--firmware", str(tmp_path / "missing.elf")]) == 2
    # Empty --adapters list
    assert main(["--firmware", str(fw), "--adapters", ",,", "--dry-run"]) == 1
    # Out of range index
    assert main(["--firmware", str(fw), "--adapter-index", "9", "--dry-run"]) == 1
    # .bin + explicit base
    assert (
        main(
            [
                "--firmware",
                str(fw),
                "--bin-base",
                "0x08000000",
                "--dry-run",
            ]
        )
        == 0
    )

    monkeypatch.undo()
    assert flash_mod._resolve_openocd(str(tmp_path / "nope.exe")) is None
    real = tmp_path / "openocd.exe"
    real.write_bytes(b"x")
    assert flash_mod._resolve_openocd(str(real)) == str(real)


def test_flash_no_adapters(monkeypatch, tmp_path: Path) -> None:
    fw = tmp_path / "app.elf"
    fw.write_bytes(b"\x00")
    monkeypatch.setattr("batch_stlink_flasher.flash.list_adapters", lambda: [])
    monkeypatch.setattr(
        "batch_stlink_flasher.flash._resolve_openocd",
        lambda _explicit: "openocd",
    )
    assert main(["--firmware", str(fw), "--dry-run"]) == 1
