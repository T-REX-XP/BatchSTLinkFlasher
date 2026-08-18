"""Domain models for adapters, flash config, and job state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class AdapterInfo:
    """One discovered ST-Link (or compatible) adapter."""

    serial: str
    hla_serial: str
    vid: int
    pid: int
    product: str = ""
    manufacturer: str = ""
    usb_path: str | None = None
    usb_port: int | None = None
    usb_hub: int | None = None
    # False when OpenOCD cannot bind this probe by serial (e.g. clone with serial "%").
    multi_adapter_ok: bool = True
    skip_reason: str | None = None


class JobState(Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OpenOcdPorts:
    """TCP ports for a single OpenOCD instance (must be unique across concurrent jobs)."""

    gdb: int
    telnet: int
    tcl: int

    def __post_init__(self) -> None:
        for name, value in (("gdb", self.gdb), ("telnet", self.telnet), ("tcl", self.tcl)):
            if not isinstance(value, int) or value <= 0 or value > 65535:
                raise ValueError(f"OpenOcdPorts.{name} must be a TCP port 1–65535, got {value!r}")
        if len({self.gdb, self.telnet, self.tcl}) != 3:
            raise ValueError("OpenOcdPorts gdb/telnet/tcl must be three distinct ports")


@dataclass(frozen=True)
class FlashConfig:
    """Shared flash parameters for one run (same firmware for all selected adapters)."""

    openocd_path: Path
    firmware_path: Path
    interface_cfg: str
    target_cfg: str
    bin_base_address: int | None = None
    scripts_search_path: Path | None = None
    job_timeout_sec: float = 120.0
    # OpenOCD command templates (configurable, not hardcoded).
    cmd_gdb_port: str = "gdb port {port}"
    cmd_telnet_port: str = "telnet port {port}"
    cmd_tcl_port: str = "tcl port {port}"
    cmd_hla_serial: str = "hla_serial {serial}"
    cmd_program: str = "program {file} verify reset exit"
    cmd_program_bin: str = "program {file} {address} verify reset exit"

    def firmware_kind(self) -> str:
        """Return ``elf``, ``hex``, or ``bin`` based on suffix."""
        suffix = self.firmware_path.suffix.lower()
        mapping = {".elf": "elf", ".hex": "hex", ".bin": "bin"}
        if suffix not in mapping:
            raise ValueError(
                f"Unsupported firmware type {suffix!r}; expected .elf, .hex, or .bin"
            )
        return mapping[suffix]

    def validate(self) -> None:
        """Raise ``ValueError`` if configuration is incomplete or inconsistent."""
        if not str(self.openocd_path).strip():
            raise ValueError("openocd_path is required")
        if not str(self.firmware_path).strip():
            raise ValueError("firmware_path is required")
        if not self.interface_cfg.strip():
            raise ValueError("interface_cfg is required")
        if not self.target_cfg.strip():
            raise ValueError("target_cfg is required")
        kind = self.firmware_kind()
        if kind == "bin":
            if self.bin_base_address is None:
                raise ValueError("bin_base_address is required for .bin firmware")
            if self.bin_base_address < 0:
                raise ValueError("bin_base_address must be non-negative")
        if self.job_timeout_sec <= 0:
            raise ValueError("job_timeout_sec must be positive")
