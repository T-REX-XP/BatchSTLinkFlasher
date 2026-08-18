"""Scan OpenOCD scripts directory for available interface and target configs."""

from __future__ import annotations

from pathlib import Path


def scan_scripts_directory(scripts_path: str | Path | None) -> tuple[list[str], list[str]]:
    """
    Scan the OpenOCD scripts directory for interface and target configs.

    Returns:
        Tuple of (interface_configs, target_configs) as sorted lists of
        relative paths (e.g., "interface/stlink.cfg", "target/stm32f1x.cfg").
    """
    if not scripts_path:
        return [], []

    scripts_dir = Path(scripts_path)
    if not scripts_dir.is_dir():
        return [], []

    interfaces = _scan_subdirectory(scripts_dir, "interface")
    targets = _scan_subdirectory(scripts_dir, "target")

    return interfaces, targets


def infer_scripts_dir_from_openocd(openocd_path: str | Path | None) -> Path | None:
    """Try to locate the scripts directory relative to the OpenOCD executable.

    Checks common layouts:
    - ``<exe_dir>/../share/openocd/scripts``
    - ``<exe_dir>/../openocd/scripts``
    - ``<exe_dir>/../scripts``
    """
    if not openocd_path:
        return None
    exe = Path(openocd_path)
    if not exe.is_file():
        return None
    exe_dir = exe.resolve().parent
    candidates = [
        exe_dir.parent / "share" / "openocd" / "scripts",
        exe_dir.parent / "openocd" / "scripts",
        exe_dir.parent / "scripts",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "interface").is_dir():
            return candidate
    return None


def _scan_subdirectory(scripts_dir: Path, subdir: str) -> list[str]:
    """Scan a subdirectory for .cfg files and return sorted relative paths."""
    target_dir = scripts_dir / subdir
    if not target_dir.is_dir():
        return []

    cfg_files = []
    for cfg_file in target_dir.rglob("*.cfg"):
        relative_path = cfg_file.relative_to(scripts_dir)
        cfg_files.append(str(relative_path).replace("\\", "/"))

    cfg_files.sort()
    return cfg_files


def looks_like_scripts_dir(path: str | Path) -> bool:
    """Return True if *path* is a directory that contains interface/ or target/."""
    p = Path(path)
    return p.is_dir() and ((p / "interface").is_dir() or (p / "target").is_dir())


# Well-known defaults so the dropdowns are never completely empty even
# when no scripts directory is available.
WELL_KNOWN_INTERFACES: list[str] = [
    "interface/stlink.cfg",
    "interface/stlink-v2.cfg",
    "interface/stlink-v2-1.cfg",
    "interface/stlink.cfg",
    "interface/stlink-dap.cfg",
    "interface/stlink-hla.cfg",
    "interface/jlink.cfg",
    "interface/ftdi/ulink2.cfg",
    "interface/ftdi/oocd.cfg",
]

WELL_KNOWN_TARGETS: list[str] = [
    "target/stm32f1x.cfg",
    "target/stm32f4x.cfg",
    "target/stm32f0x.cfg",
    "target/stm32f7x.cfg",
    "target/stm32h7x.cfg",
    "target/stm32l4x.cfg",
    "target/nrf52.cfg",
    "target/atsame5x.cfg",
]


def get_default_interface_config() -> str:
    """Return the default interface config path."""
    return "interface/stlink.cfg"


def get_default_target_config() -> str:
    """Return the default target config path."""
    return "target/stm32f1x.cfg"
