"""OpenOCD argv builder (process runner arrives in Phase 3)."""

from __future__ import annotations

import shlex
from pathlib import Path

from batch_stlink_flasher.flashing.models import FlashConfig, OpenOcdPorts

_DEFAULT_BIN_BASE = 0x08000000


def build_program_command(firmware_path: Path, *, bin_base_address: int | None) -> str:
    """
    Build the OpenOCD Tcl ``program … verify reset exit`` statement.

    ``.elf`` / ``.hex``: address is taken from the image.
    ``.bin``: ``bin_base_address`` is required (caller should validate via ``FlashConfig``).
    """
    path = _openocd_path_literal(firmware_path)
    suffix = firmware_path.suffix.lower()
    if suffix == ".bin":
        if bin_base_address is None:
            raise ValueError("bin_base_address is required for .bin firmware")
        return f"program {path} {bin_base_address:#x} verify reset exit"
    if suffix in {".elf", ".hex"}:
        return f"program {path} verify reset exit"
    raise ValueError(f"Unsupported firmware type {suffix!r}; expected .elf, .hex, or .bin")


def build_openocd_command(
    config: FlashConfig,
    hla_serial: str,
    ports: OpenOcdPorts,
) -> list[str]:
    """
    Build an argv list suitable for ``subprocess`` / ``QProcess``.

    Always binds ``hla_serial`` and unique ports so multiple adapters can run in parallel.
    """
    config.validate()
    serial = hla_serial.strip()
    if not serial:
        raise ValueError("hla_serial is required")

    argv: list[str] = [str(config.openocd_path)]

    if config.scripts_search_path is not None:
        argv.extend(["-s", str(config.scripts_search_path)])

    argv.extend(
        [
            "-f",
            config.interface_cfg,
            "-f",
            config.target_cfg,
            "-c",
            f"hla_serial {serial}",
            "-c",
            f"gdb_port {ports.gdb}",
            "-c",
            f"telnet_port {ports.telnet}",
            "-c",
            f"tcl_port {ports.tcl}",
            "-c",
            build_program_command(
                config.firmware_path,
                bin_base_address=config.bin_base_address,
            ),
        ]
    )
    return argv


def format_command_for_shell(argv: list[str]) -> str:
    """Render argv as a copy-pasteable shell command (POSIX-style quoting via shlex)."""
    return " ".join(shlex.quote(part) for part in argv)


def _openocd_path_literal(path: Path) -> str:
    """
    Quote a filesystem path for embedding inside an OpenOCD ``-c`` Tcl string.

    Uses double quotes and escapes backslashes / quotes so Windows paths work.
    """
    text = str(path)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def default_bin_base_address() -> int:
    """STM32 flash base commonly used when flashing raw ``.bin`` images."""
    return _DEFAULT_BIN_BASE
