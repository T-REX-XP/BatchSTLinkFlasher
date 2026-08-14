"""Sanity checks for installer packaging files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_scripts_exist() -> None:
    assert (ROOT / "scripts" / "install_build_deps.ps1").is_file()
    assert (ROOT / "scripts" / "build_app.ps1").is_file()
    assert (ROOT / "scripts" / "build_installer.ps1").is_file()
    assert (ROOT / "scripts" / "build_all.ps1").is_file()
    assert (ROOT / "scripts" / "README.md").is_file()
    assert (ROOT / "scripts" / "install.ps1").is_file()
    assert (ROOT / "scripts" / "uninstall.ps1").is_file()
    assert (ROOT / "scripts" / "fetch_runtime_deps.ps1").is_file()
    assert (ROOT / "scripts" / "create_release_tag.ps1").is_file()
    assert (ROOT / "packaging" / "installer.iss").is_file()
    assert (ROOT / "packaging" / "runtime-deps.json").is_file()
    assert (ROOT / ".github" / "workflows" / "release.yml").is_file()


def test_scripts_readme_documents_three_steps() -> None:
    text = (ROOT / "scripts" / "README.md").read_text(encoding="utf-8")
    assert "install_build_deps.ps1" in text
    assert "build_app.ps1" in text
    assert "build_installer.ps1" in text


def test_release_workflow_tag_filter() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "v[0-9]+.[0-9]+.[0-9]+" in text
    assert "softprops/action-gh-release" in text
    assert "install_build_deps.ps1" in text
    assert "build_app.ps1" in text
    assert "build_installer.ps1" in text


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
    assert "SetupIconFile=" in text
    assert "app_icon.ico" in text
    assert "WizardImageFile=" in text
    assert "wizard_image.bmp" in text
    assert "WizardSmallImageFile=" in text
    assert "wizard_small.bmp" in text


def test_app_icon_ico_is_valid_multisize() -> None:
    import struct

    ico = ROOT / "src" / "batch_stlink_flasher" / "assets" / "app_icon.ico"
    assert ico.is_file()
    data = ico.read_bytes()
    reserved, typ, count = struct.unpack_from("<HHH", data, 0)
    assert reserved == 0
    assert typ == 1
    assert count >= 4
    offset = 6
    for _ in range(count):
        _w, _h, _c, _r, _planes, _bpp, size, off = struct.unpack_from("<BBBBHHII", data, offset)
        assert size > 0
        assert off + size <= len(data)
        offset += 16
    assert (ROOT / "src" / "batch_stlink_flasher" / "assets" / "wizard_image.bmp").is_file()
    assert (ROOT / "src" / "batch_stlink_flasher" / "assets" / "wizard_small.bmp").is_file()


def test_runtime_deps_manifest() -> None:
    data = json.loads((ROOT / "packaging" / "runtime-deps.json").read_text(encoding="utf-8"))
    assert "openocd" in data
    assert data["openocd"]["url"].startswith("https://")
    assert len(data["openocd"]["sha256"]) == 64


def test_build_installer_bundles_openocd() -> None:
    text = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
    assert "tools\\openocd" in text or "tools/openocd" in text
    assert "bundled-tools.json" in text
