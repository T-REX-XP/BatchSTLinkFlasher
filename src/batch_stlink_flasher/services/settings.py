"""Persisted operator settings via QSettings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings

ORG = "BatchSTLinkFlasher"
APP = "BatchSTLinkFlasher"
DEFAULT_BIN_BASE = "0x08000000"


@dataclass
class AppSettings:
    openocd_path: str = "openocd"
    last_firmware_path: str = ""
    interface_cfg: str = "interface/stlink.cfg"
    target_cfg: str = "target/stm32f1x.cfg"
    scripts_search_path: str = ""
    bin_base_address: str = DEFAULT_BIN_BASE
    job_timeout_sec: float = 120.0


def load_settings() -> AppSettings:
    q = QSettings(ORG, APP)
    return AppSettings(
        openocd_path=str(q.value("openocd_path", "openocd")),
        last_firmware_path=str(q.value("last_firmware_path", "")),
        interface_cfg=str(q.value("interface_cfg", "interface/stlink.cfg")),
        target_cfg=str(q.value("target_cfg", "target/stm32f1x.cfg")),
        scripts_search_path=str(q.value("scripts_search_path", "")),
        bin_base_address=str(q.value("bin_base_address", DEFAULT_BIN_BASE)),
        job_timeout_sec=float(q.value("job_timeout_sec", 120.0)),
    )


def save_settings(settings: AppSettings) -> None:
    q = QSettings(ORG, APP)
    q.setValue("openocd_path", settings.openocd_path)
    q.setValue("last_firmware_path", settings.last_firmware_path)
    q.setValue("interface_cfg", settings.interface_cfg)
    q.setValue("target_cfg", settings.target_cfg)
    q.setValue("scripts_search_path", settings.scripts_search_path)
    q.setValue("bin_base_address", settings.bin_base_address)
    q.setValue("job_timeout_sec", settings.job_timeout_sec)
    q.sync()


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
    return Path(found) if found else None
