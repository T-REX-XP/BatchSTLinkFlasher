"""Resolve packaged UI asset paths (dev install and PyInstaller)."""

from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path


def asset_path(name: str) -> Path | None:
    """Return filesystem path to ``assets/<name>``, or ``None`` if missing."""
    # PyInstaller onedir / onefile extraction
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / "batch_stlink_flasher" / "assets" / name
        if candidate.is_file():
            return candidate
        candidate = Path(meipass) / "assets" / name
        if candidate.is_file():
            return candidate

    try:
        root = resources.files("batch_stlink_flasher") / "assets" / name
        with resources.as_file(root) as path:
            if path.is_file():
                return Path(path)
    except (FileNotFoundError, ModuleNotFoundError, TypeError, OSError):
        pass

    # Editable / source tree fallback
    fallback = Path(__file__).resolve().parent / "assets" / name
    if fallback.is_file():
        return fallback
    return None
