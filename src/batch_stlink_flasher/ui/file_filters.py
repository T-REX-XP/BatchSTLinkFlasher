"""Shared QFileDialog name filters (file masks) for browse dialogs."""

from __future__ import annotations

import sys

# Firmware accepted by FlashConfig / validation (FR-CFG-01).
FIRMWARE_FILTER = (
    "Firmware (*.elf *.hex *.bin);;"
    "ELF (*.elf);;"
    "Intel HEX (*.hex);;"
    "Binary (*.bin);;"
    "All files (*.*)"
)

# OpenOCD Tcl/board/interface scripts (FR-CFG-03).
OPENOCD_CFG_FILTER = "OpenOCD config (*.cfg);;All files (*.*)"

# Session log export (FR-LOG-06).
LOG_EXPORT_FILTER = "Text (*.log *.txt);;JSON (*.json)"


def openocd_executable_filter() -> str:
    """Platform-aware filter for selecting the OpenOCD binary (FR-CFG-04)."""
    if sys.platform == "win32":
        return (
            "OpenOCD (openocd.exe);;"
            "Executables (*.exe);;"
            "All files (*.*)"
        )
    return "OpenOCD (openocd);;All files (*)"
