"""Version / bump helpers tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_json_shape() -> None:
    data = json.loads((ROOT / "packaging" / "version.json").read_text(encoding="utf-8"))
    assert {"major", "minor", "patch", "build"} <= set(data)
    assert all(isinstance(data[k], int) and data[k] >= 0 for k in ("major", "minor", "patch", "build"))


def test_runtime_version_matches_version_json() -> None:
    from batch_stlink_flasher import __version__, __version_info__

    data = json.loads((ROOT / "packaging" / "version.json").read_text(encoding="utf-8"))
    expected = f"{data['major']}.{data['minor']}.{data['patch']}.{data['build']}"
    assert __version__ == expected
    assert __version_info__ == (data["major"], data["minor"], data["patch"], data["build"])


def test_pyproject_version_matches() -> None:
    data = json.loads((ROOT / "packaging" / "version.json").read_text(encoding="utf-8"))
    expected = f"{data['major']}.{data['minor']}.{data['patch']}.{data['build']}"
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert match is not None
    assert match.group(1) == expected


def test_bump_scripts_exist() -> None:
    assert (ROOT / "scripts" / "bump_version.ps1").is_file()
    assert (ROOT / "scripts" / "version.ps1").is_file()
    assert "Incrementing build version" in (ROOT / "scripts" / "build_windows.ps1").read_text(
        encoding="utf-8"
    )
