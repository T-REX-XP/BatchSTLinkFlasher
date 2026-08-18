"""OpenOCD argv builder and helpers."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from batch_stlink_flasher.flashing.models import FlashConfig, OpenOcdPorts

_DEFAULT_BIN_BASE = 0x08000000
_ERROR_HINT = re.compile(r"(error|fail|couldn't|unable|timeout)", re.IGNORECASE)


def build_program_command(
    firmware_path: Path,
    *,
    bin_base_address: int | None,
    cmd_template: str = "program {file} verify reset exit",
    cmd_template_bin: str = "program {file} {address} verify reset exit",
) -> str:
    """
    Build the OpenOCD Tcl ``program … verify reset exit`` statement.

    Uses configurable command templates from settings.
    ``.elf`` / ``.hex``: address is taken from the image.
    ``.bin``: ``bin_base_address`` is required (caller should validate via ``FlashConfig``).
    """
    path = _openocd_path_literal(firmware_path)
    suffix = firmware_path.suffix.lower()
    if suffix == ".bin":
        if bin_base_address is None:
            raise ValueError("bin_base_address is required for .bin firmware")
        return cmd_template_bin.replace("{file}", path).replace("{address}", f"{bin_base_address:#x}")
    if suffix in {".elf", ".hex"}:
        return cmd_template.replace("{file}", path)
    raise ValueError(f"Unsupported firmware type {suffix!r}; expected .elf, .hex, or .bin")


def build_openocd_command(
    config: FlashConfig,
    hla_serial: str | None,
    ports: OpenOcdPorts,
) -> list[str]:
    """
    Build an argv list suitable for ``subprocess`` / ``QProcess``.

    When ``hla_serial`` is empty/None, the serial bind is omitted (single-adapter /
    clone probes with unusable USB serial). Unique ports are always set.
    """
    config.validate()

    argv: list[str] = [str(config.openocd_path)]

    if config.scripts_search_path is not None:
        argv.extend(["-s", str(config.scripts_search_path)])

    argv.extend(
        [
            "-f",
            config.interface_cfg,
            "-f",
            config.target_cfg,
        ]
    )

    serial = (hla_serial or "").strip()
    if serial:
        argv.extend(["-c", config.cmd_hla_serial.replace("{serial}", serial)])

    program_cmd = build_program_command(
        config.firmware_path,
        bin_base_address=config.bin_base_address,
        cmd_template=config.cmd_program,
        cmd_template_bin=config.cmd_program_bin,
    )
    argv.extend(
        [
            "-c",
            config.cmd_gdb_port.replace("{port}", str(ports.gdb)),
            "-c",
            config.cmd_telnet_port.replace("{port}", str(ports.telnet)),
            "-c",
            config.cmd_tcl_port.replace("{port}", str(ports.tcl)),
            "-c",
            program_cmd,
        ]
    )
    return argv


def format_command_for_shell(argv: list[str]) -> str:
    """Render argv as a copy-pasteable shell command (POSIX-style quoting via shlex)."""
    return " ".join(shlex.quote(part) for part in argv)


def summarize_openocd_error(log_lines: list[str], *, exit_code: int | None) -> str:
    """Pick the most useful failure line from OpenOCD output."""
    for line in reversed(log_lines):
        text = line.strip()
        if text and _ERROR_HINT.search(text):
            return text
    if log_lines:
        return log_lines[-1].strip() or f"OpenOCD exited with code {exit_code}"
    return f"OpenOCD exited with code {exit_code}"


def default_bin_base_address() -> int:
    """STM32 flash base commonly used when flashing raw ``.bin`` images."""
    return _DEFAULT_BIN_BASE


def _openocd_path_literal(path: Path) -> str:
    """
    Quote a filesystem path for embedding inside an OpenOCD ``-c`` Tcl string.

    Uses double quotes and escapes backslashes / quotes so Windows paths work.
    """
    text = str(path)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
