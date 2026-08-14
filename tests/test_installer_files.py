"""Sanity checks for installer packaging files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_scripts_exist() -> None:
    assert (ROOT / "scripts" / "install.ps1").is_file()
    assert (ROOT / "scripts" / "uninstall.ps1").is_file()
    assert (ROOT / "scripts" / "build_installer.ps1").is_file()
    assert (ROOT / "scripts" / "build_full_installer.ps1").is_file()
    assert (ROOT / "scripts" / "fetch_runtime_deps.ps1").is_file()
    assert (ROOT / "packaging" / "installer.iss").is_file()
    assert (ROOT / "packaging" / "runtime-deps.json").is_file()


def test_runtime_deps_manifest() -> None:
    data = json.loads((ROOT / "packaging" / "runtime-deps.json").read_text(encoding="utf-8"))
    assert "openocd" in data
    assert data["openocd"]["url"].startswith("https://")
    assert len(data["openocd"]["sha256"]) == 64


def test_full_installer_script_mentions_openocd() -> None:
    text = (ROOT / "scripts" / "build_full_installer.ps1").read_text(encoding="utf-8")
    assert "fetch_runtime_deps.ps1" in text
    assert "tools\\openocd" in text or "tools/openocd" in text
    assert "bundled-tools.json" in text


def test_installer_script_reads_version_helper() -> None:
    text = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    assert "version.ps1" in text
    assert "BatchSTLinkFlasher.exe" in text
    assert "UninstallString" in text


def test_inno_script_points_at_dist() -> None:
    data = json.loads((ROOT / "packaging" / "version.json").read_text(encoding="utf-8"))
    expected = f"{data['major']}.{data['minor']}.{data['patch']}.{data['build']}"
    text = (ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8")
    assert r"..\dist\BatchSTLinkFlasher\*" in text
    assert "BatchSTLinkFlasher.exe" in text
    assert f'#define MyAppVersion "{expected}"' in text
