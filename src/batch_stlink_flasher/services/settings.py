"""Persisted operator settings via QSettings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QSettings

from batch_stlink_flasher.bundled_tools import discover_bundled_tools

ORG = "BatchSTLinkFlasher"
APP = "BatchSTLinkFlasher"
DEFAULT_BIN_BASE = "0x08000000"


class FlashMode(str, Enum):
    """How FlashOrchestrator schedules selected adapters."""

    AUTO = "auto"
    """HLA-bound probes in parallel; clones sequential with USB isolation."""

    SEQUENTIAL = "sequential"
    """One adapter at a time (HLA still uses hla_serial; clones still isolate)."""


def normalize_flash_mode(value: str | FlashMode | None) -> FlashMode:
    if isinstance(value, FlashMode):
        return value
    text = (value or "").strip().lower()
    if text in {FlashMode.SEQUENTIAL.value, "seq", "always_sequential"}:
        return FlashMode.SEQUENTIAL
    return FlashMode.AUTO


@dataclass
class AppSettings:
    openocd_path: str = "openocd"
    last_firmware_path: str = ""
    interface_cfg: str = "interface/stlink.cfg"
    target_cfg: str = "target/stm32f1x.cfg"
    scripts_search_path: str = ""
    bin_base_address: str = DEFAULT_BIN_BASE
    job_timeout_sec: float = 120.0
    theme_mode: str = "system"  # system | light | dark
    flash_mode: str = FlashMode.AUTO.value  # auto | sequential
    # OpenOCD command templates — stored in config, not hardcoded.
    openocd_cmd_gdb_port: str = "gdb port {port}"
    openocd_cmd_telnet_port: str = "telnet port {port}"
    openocd_cmd_tcl_port: str = "tcl port {port}"
    openocd_cmd_hla_serial: str = "hla_serial {serial}"
    openocd_cmd_program: str = "program {file} verify reset exit"
    openocd_cmd_program_bin: str = "program {file} {address} verify reset exit"


def load_settings() -> AppSettings:
    q = QSettings(ORG, APP)
    settings = AppSettings(
        openocd_path=str(q.value("openocd_path", "openocd")),
        last_firmware_path=str(q.value("last_firmware_path", "")),
        interface_cfg=str(q.value("interface_cfg", "interface/stlink.cfg")),
        target_cfg=str(q.value("target_cfg", "target/stm32f1x.cfg")),
        scripts_search_path=str(q.value("scripts_search_path", "")),
        bin_base_address=str(q.value("bin_base_address", DEFAULT_BIN_BASE)),
        job_timeout_sec=float(q.value("job_timeout_sec", 120.0)),
        theme_mode=str(q.value("theme_mode", "system")),
        flash_mode=normalize_flash_mode(str(q.value("flash_mode", FlashMode.AUTO.value))).value,
        openocd_cmd_gdb_port=str(q.value("openocd_cmd_gdb_port", "gdb port {port}")),
        openocd_cmd_telnet_port=str(q.value("openocd_cmd_telnet_port", "telnet port {port}")),
        openocd_cmd_tcl_port=str(q.value("openocd_cmd_tcl_port", "tcl port {port}")),
        openocd_cmd_hla_serial=str(q.value("openocd_cmd_hla_serial", "hla_serial {serial}")),
        openocd_cmd_program=str(q.value("openocd_cmd_program", "program {file} verify reset exit")),
        openocd_cmd_program_bin=str(q.value("openocd_cmd_program_bin", "program {file} {address} verify reset exit")),
    )
    return apply_bundled_defaults(settings)


def save_settings(settings: AppSettings) -> None:
    q = QSettings(ORG, APP)
    q.setValue("openocd_path", settings.openocd_path)
    q.setValue("last_firmware_path", settings.last_firmware_path)
    q.setValue("interface_cfg", settings.interface_cfg)
    q.setValue("target_cfg", settings.target_cfg)
    q.setValue("scripts_search_path", settings.scripts_search_path)
    q.setValue("bin_base_address", settings.bin_base_address)
    q.setValue("job_timeout_sec", settings.job_timeout_sec)
    q.setValue("theme_mode", settings.theme_mode)
    q.setValue("flash_mode", normalize_flash_mode(settings.flash_mode).value)
    q.setValue("openocd_cmd_gdb_port", settings.openocd_cmd_gdb_port)
    q.setValue("openocd_cmd_telnet_port", settings.openocd_cmd_telnet_port)
    q.setValue("openocd_cmd_tcl_port", settings.openocd_cmd_tcl_port)
    q.setValue("openocd_cmd_hla_serial", settings.openocd_cmd_hla_serial)
    q.setValue("openocd_cmd_program", settings.openocd_cmd_program)
    q.setValue("openocd_cmd_program_bin", settings.openocd_cmd_program_bin)
    q.sync()


def apply_bundled_defaults(settings: AppSettings) -> AppSettings:
    """
    If OpenOCD is still the default ``openocd`` name (or missing), prefer a
    bundled copy shipped under ``tools/openocd``.
    """
    bundled = discover_bundled_tools()
    if bundled is None:
        return settings

    current = resolve_openocd_path(settings.openocd_path)
    use_bundled_exe = current is None or settings.openocd_path.strip() in {"", "openocd", "openocd.exe"}
    if use_bundled_exe:
        settings.openocd_path = str(bundled.openocd_exe)

    if not settings.scripts_search_path.strip() and bundled.scripts_dir is not None:
        settings.scripts_search_path = str(bundled.scripts_dir)
    return settings


def resolve_openocd_path(value: str) -> Path | None:
    """Return an existing OpenOCD path, or None if not found."""
    import shutil

    text = (value or "").strip()
    if not text:
        return None

    path = Path(text)
    if path.is_file():
        return path
    found = shutil.which(text)
    if found:
        return Path(found)

    if text.lower() in {"openocd", "openocd.exe"}:
        bundled = discover_bundled_tools()
        if bundled is not None and bundled.openocd_exe.is_file():
            return bundled.openocd_exe
    return None
