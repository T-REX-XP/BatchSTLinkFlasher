"""Locate tools bundled next to the frozen app (or vendor tree in dev)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BundledTools:
    openocd_exe: Path
    scripts_dir: Path | None
    openocd_version: str = ""
    openocd_name: str = ""


def app_base_dir() -> Path:
    """Directory that contains the executable (frozen) or package root (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # src/batch_stlink_flasher/bundled_tools.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def _candidate_roots() -> list[Path]:
    base = app_base_dir()
    roots = [
        base / "tools" / "openocd",
        base / "vendor" / "runtime" / "openocd",
    ]
    # Editable install: package under src/, vendor at repo root
    if not getattr(sys, "frozen", False):
        roots.append(Path(__file__).resolve().parents[2] / "vendor" / "runtime" / "openocd")
    return roots


def discover_bundled_tools() -> BundledTools | None:
    """
    Return bundled OpenOCD paths if present.

  Prefer ``bundled-tools.json`` next to the EXE; otherwise probe conventional
  ``tools/openocd`` / ``vendor/runtime/openocd`` layouts.
    """
    base = app_base_dir()
    meta_path = base / "bundled-tools.json"
    if meta_path.is_file():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            exe = base / str(data.get("OpenOcdExe") or "tools/openocd/bin/openocd.exe")
            scripts_raw = data.get("OpenOcdScripts")
            scripts = (base / str(scripts_raw)) if scripts_raw else None
            if exe.is_file():
                return BundledTools(
                    openocd_exe=exe,
                    scripts_dir=scripts if scripts and scripts.is_dir() else None,
                    openocd_version=str(data.get("OpenOcdVersion") or ""),
                    openocd_name=str(data.get("OpenOcdName") or ""),
                )
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    for root in _candidate_roots():
        exe = root / "bin" / "openocd.exe"
        if not exe.is_file():
            exe = root / "bin" / "openocd"
        if not exe.is_file():
            continue
        # Try standard layout first, then the nested layout used by some bundles
        # (e.g. vendor/runtime/openocd/openocd/scripts).
        scripts = root / "share" / "openocd" / "scripts"
        if not scripts.is_dir():
            scripts = root / "openocd" / "scripts"
        return BundledTools(
            openocd_exe=exe,
            scripts_dir=scripts if scripts.is_dir() else None,
        )
    return None
