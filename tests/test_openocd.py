"""Unit tests for OpenOCD argv builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_stlink_flasher.flashing.models import FlashConfig, OpenOcdPorts
from batch_stlink_flasher.flashing.openocd import (
    build_openocd_command,
    build_program_command,
    default_bin_base_address,
    format_command_for_shell,
)


@pytest.fixture
def ports() -> OpenOcdPorts:
    return OpenOcdPorts(gdb=3333, telnet=4444, tcl=6666)


def _config(tmp_path: Path, name: str, **kwargs: object) -> FlashConfig:
    defaults: dict[str, object] = {
        "openocd_path": Path("C:/tools/openocd.exe"),
        "firmware_path": tmp_path / name,
        "interface_cfg": "interface/stlink.cfg",
        "target_cfg": "target/stm32f1x.cfg",
    }
    defaults.update(kwargs)
    return FlashConfig(**defaults)  # type: ignore[arg-type]


def test_build_program_command_elf(tmp_path: Path) -> None:
    path = tmp_path / "fw.elf"
    cmd = build_program_command(path, bin_base_address=None)
    assert cmd.startswith("program ")
    assert cmd.endswith("verify reset exit")
    before_verify = cmd.split(" verify ", 1)[0]
    assert before_verify.startswith("program ")
    assert "0x" not in before_verify.split()[-1]


def test_build_program_command_hex(tmp_path: Path) -> None:
    path = tmp_path / "fw.hex"
    cmd = build_program_command(path, bin_base_address=None)
    assert "fw.hex" in cmd
    assert cmd.endswith("verify reset exit")


def test_build_program_command_bin_with_address(tmp_path: Path) -> None:
    path = tmp_path / "fw.bin"
    cmd = build_program_command(path, bin_base_address=0x08000000)
    assert "0x8000000" in cmd
    assert cmd.endswith("verify reset exit")


def test_build_program_command_bin_requires_address(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bin_base_address"):
        build_program_command(tmp_path / "fw.bin", bin_base_address=None)


def test_build_openocd_command_elf(tmp_path: Path, ports: OpenOcdPorts) -> None:
    cfg = _config(tmp_path, "app.elf")
    argv = build_openocd_command(cfg, "66FF67065648574854362567", ports)

    assert argv[0] == str(cfg.openocd_path)
    assert argv[1:5] == [
        "-f",
        "interface/stlink.cfg",
        "-f",
        "target/stm32f1x.cfg",
    ]
    assert "-c" in argv
    assert "hla_serial 66FF67065648574854362567" in argv
    assert "gdb_port 3333" in argv
    assert "telnet_port 4444" in argv
    assert "tcl_port 6666" in argv

    program = argv[argv.index("tcl_port 6666") + 2]
    assert program.startswith("program ")
    assert "verify reset exit" in program
    # .elf must not inject a flash base address token before verify
    before_verify = program.split(" verify ", 1)[0]
    assert "0x" not in before_verify.split()[-1]


def test_build_openocd_command_hex(tmp_path: Path, ports: OpenOcdPorts) -> None:
    cfg = _config(tmp_path, "app.hex")
    argv = build_openocd_command(cfg, "SERIAL1", ports)
    program = [a for a in argv if a.startswith("program ")][0]
    assert "app.hex" in program
    assert "verify reset exit" in program


def test_build_openocd_command_bin(tmp_path: Path, ports: OpenOcdPorts) -> None:
    cfg = _config(tmp_path, "app.bin", bin_base_address=default_bin_base_address())
    argv = build_openocd_command(cfg, "SERIAL1", ports)
    program = [a for a in argv if a.startswith("program ")][0]
    assert "0x8000000" in program
    assert "app.bin" in program


def test_build_openocd_command_includes_scripts_search_path(
    tmp_path: Path, ports: OpenOcdPorts
) -> None:
    scripts = tmp_path / "scripts"
    cfg = _config(tmp_path, "app.elf", scripts_search_path=scripts)
    argv = build_openocd_command(cfg, "S1", ports)
    assert argv[1:3] == ["-s", str(scripts)]


def test_build_openocd_command_omits_empty_serial(
    tmp_path: Path, ports: OpenOcdPorts
) -> None:
    cfg = _config(tmp_path, "app.elf")
    argv = build_openocd_command(cfg, "  ", ports)
    assert not any(isinstance(a, str) and a.startswith("hla_serial") for a in argv)
    assert "gdb_port 3333" in argv


def test_build_openocd_command_rejects_bin_without_address(
    tmp_path: Path, ports: OpenOcdPorts
) -> None:
    cfg = _config(tmp_path, "app.bin")
    with pytest.raises(ValueError, match="bin_base_address"):
        build_openocd_command(cfg, "S1", ports)


def test_format_command_for_shell(tmp_path: Path, ports: OpenOcdPorts) -> None:
    cfg = _config(tmp_path, "app.elf")
    argv = build_openocd_command(cfg, "S1", ports)
    rendered = format_command_for_shell(argv)
    assert "openocd" in rendered.lower() or "openocd.exe" in rendered.lower()
    assert "hla_serial" in rendered
