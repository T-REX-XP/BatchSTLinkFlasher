# Packaging & installer

Primary how-to: **[scripts/README.md](../scripts/README.md)**.

## Goal artifacts

| Artifact | Description |
|----------|-------------|
| **`BatchSTLinkFlasher-<version>-Setup.exe`** | Single Windows installer for operators (Inno Setup) |
| `dist\BatchSTLinkFlasher\BatchSTLinkFlasher.exe` | App EXE inside an onedir layout (+ Qt DLLs) |
| `tools\openocd\` | Bundled OpenOCD next to the EXE (added in step 3) |
| `…-portable.zip` | Optional zip of the onedir folder |

Operators should ship/download **Setup.exe**. After install they launch
`BatchSTLinkFlasher.exe` from the install directory.

### Why onedir + Setup.exe (not PyInstaller `--onefile`)

- PySide6/Qt needs plugins beside the process.
- OpenOCD is a full tree (`bin` + `share/openocd/scripts`), not one binary.
- Inno Setup compresses the folder into **one installer EXE** — that is the
  “single file” distribution.

## Recommended build pipeline (3 steps)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_build_deps.ps1 -InstallSystemDeps
powershell -ExecutionPolicy Bypass -File scripts\build_app.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -ZipPortable
```

Or all at once (also tries to install Inno if needed):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_all.ps1 -ZipPortable -InstallSystemDeps -InstallInno
```

| Step | Script | Output |
|------|--------|--------|
| 1 | `install_build_deps.ps1` | `.venv`, OpenOCD under `vendor\runtime\`, optional Inno |
| 2 | `build_app.ps1` | `dist\BatchSTLinkFlasher\` via `packaging/batch_stlink_flasher.spec` |
| 3 | `build_installer.ps1` | OpenOCD bundle + **Setup.exe** (+ optional zip) |

## Inno Setup (required for Setup.exe)

`build_installer.ps1` looks for `ISCC.exe` and **fails** if missing (unless
`-SkipInno`).

Install options:

```powershell
winget install JRSoftware.InnoSetup
# or
choco install innosetup
# or during packaging:
powershell -File scripts\build_installer.ps1 -InstallInno -ZipPortable
```

Script: `packaging/installer.iss` (version synced from `packaging/version.json`).

## Operator runtime

| Dependency | How it is provided |
|------------|--------------------|
| **Python** | Embedded in `BatchSTLinkFlasher.exe` (PyInstaller) |
| **OpenOCD** | `tools\openocd\` via `build_installer.ps1` |
| **VC++ runtime** | Optional via `-InstallSystemDeps` |
| **ST-Link USB driver** | Optional; Windows PnP with ST’s driver |

Pinned OpenOCD: `packaging/runtime-deps.json` (xPack OpenOCD).

## Install without Setup.exe

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -DesktopShortcut -Force
powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
```

## GitHub Actions

### CI (`.github/workflows/ci.yml`)

Push/PR: tests with coverage ≥ 85%.

### Release (`.github/workflows/release.yml`)

Tag **`vMAJOR.MINOR.PATCH`** (e.g. `v0.1.0`):

1. Install deps + Inno Setup (Chocolatey)
2. `build_app.ps1 -NoBump`
3. `build_installer.ps1 -ZipPortable` → publishes Setup.exe + portable zip

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_release_tag.ps1 -Version 0.1.0 -Commit -Push
```

## Branding / icons

```powershell
.\.venv\Scripts\python scripts\generate_app_icon.py
```

## Versioning

Source of truth: `packaging/version.json` (`major.minor.patch.build`).

```powershell
powershell -File scripts\build_app.ps1          # bumps build
powershell -File scripts\build_app.ps1 -NoBump  # keep version
powershell -File scripts\bump_version.ps1 -Patch
```

`bump_version.ps1` / build scripts sync `_version.py`, `pyproject.toml`, and
`packaging/installer.iss`.
