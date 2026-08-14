"""Bundled OpenOCD / tools discovery tests."""

from __future__ import annotations

import json
from pathlib import Path

from batch_stlink_flasher.bundled_tools import discover_bundled_tools
from batch_stlink_flasher.services.settings import (
    AppSettings,
    apply_bundled_defaults,
    resolve_openocd_path,
)


def test_discover_bundled_from_json(tmp_path: Path, monkeypatch) -> None:
    tools = tmp_path / "tools" / "openocd" / "bin"
    tools.mkdir(parents=True)
    exe = tools / "openocd.exe"
    exe.write_bytes(b"MZ")
    scripts = tmp_path / "tools" / "openocd" / "share" / "openocd" / "scripts"
    scripts.mkdir(parents=True)
    (tmp_path / "bundled-tools.json").write_text(
        json.dumps(
            {
                "OpenOcdExe": "tools/openocd/bin/openocd.exe",
                "OpenOcdScripts": "tools/openocd/share/openocd/scripts",
                "OpenOcdVersion": "0.12.0-7",
                "OpenOcdName": "xPack OpenOCD",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("batch_stlink_flasher.bundled_tools.app_base_dir", lambda: tmp_path)
    found = discover_bundled_tools()
    assert found is not None
    assert found.openocd_exe == exe
    assert found.scripts_dir == scripts
    assert found.openocd_version == "0.12.0-7"


def test_apply_bundled_defaults(tmp_path: Path, monkeypatch) -> None:
    tools = tmp_path / "tools" / "openocd" / "bin"
    tools.mkdir(parents=True)
    exe = tools / "openocd.exe"
    exe.write_bytes(b"MZ")
    scripts = tmp_path / "tools" / "openocd" / "share" / "openocd" / "scripts"
    scripts.mkdir(parents=True)
    monkeypatch.setattr(
        "batch_stlink_flasher.services.settings.discover_bundled_tools",
        lambda: __import__(
            "batch_stlink_flasher.bundled_tools", fromlist=["BundledTools"]
        ).BundledTools(openocd_exe=exe, scripts_dir=scripts),
    )
    settings = apply_bundled_defaults(AppSettings(openocd_path="openocd"))
    assert settings.openocd_path == str(exe)
    assert settings.scripts_search_path == str(scripts)
    assert resolve_openocd_path("openocd") == exe


def test_resolve_ignores_unknown_name() -> None:
    assert resolve_openocd_path("definitely-not-openocd-xyz") is None
