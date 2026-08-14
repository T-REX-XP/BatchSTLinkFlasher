"""Sanity checks for installer packaging files."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_scripts_exist() -> None:
    assert (ROOT / "scripts" / "install.ps1").is_file()
    assert (ROOT / "scripts" / "uninstall.ps1").is_file()
    assert (ROOT / "scripts" / "build_installer.ps1").is_file()
    assert (ROOT / "packaging" / "installer.iss").is_file()


def test_installer_script_mentions_version_and_exe() -> None:
    text = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    assert "0.1.0" in text
    assert "BatchSTLinkFlasher.exe" in text
    assert "UninstallString" in text


def test_inno_script_points_at_dist() -> None:
    text = (ROOT / "packaging" / "installer.iss").read_text(encoding="utf-8")
    assert r"..\dist\BatchSTLinkFlasher\*" in text
    assert "BatchSTLinkFlasher.exe" in text
