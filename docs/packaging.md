# Packaging & installer

## Operator runtime dependencies

- Windows 10/11 x64
- [OpenOCD](https://openocd.org/) installed and on `PATH` (or configured in the app)
- ST-Link USB driver (ST official driver is fine; Windows PnP discovery does not need libusb)
- Optional: [stlink](https://github.com/stlink-org/stlink) (`st-info`) for richer probe info

The app does **not** bundle OpenOCD in v0.1.0.

## Dev bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

Creates `.venv`, installs `[dev]`, runs tests, and prints docs links.

## Build Windows dist (PyInstaller onedir)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Output folder: `dist\BatchSTLinkFlasher\`

## Installer (recommended)

### Option A — PowerShell installer (no third-party tools)

Builds (optional) and installs per-user under `%LOCALAPPDATA%\Programs\BatchSTLinkFlasher`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Build -DesktopShortcut -Force
```

Useful switches:

| Switch | Meaning |
|--------|---------|
| `-Build` | Run PyInstaller build first |
| `-DesktopShortcut` | Create Desktop icon |
| `-AllUsers` | Install to Program Files (needs admin) |
| `-Force` | Overwrite without prompt |
| `-SourceDir path` | Use an existing onedir folder |

Uninstall:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
```

Or use **Settings → Apps** / Start Menu → Uninstall.

### Option B — Setup.exe (Inno Setup)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -ZipPortable
```

Produces:

- `dist\BatchSTLinkFlasher\` (onedir)
- `dist\BatchSTLinkFlasher-0.1.0-Setup.exe` (when ISCC is available)
- `dist\BatchSTLinkFlasher-0.1.0-portable.zip` (with `-ZipPortable`)

Inno script: `packaging\installer.iss`

### Option C — Portable zip only

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -SkipInno -ZipPortable
```

Unzip and run `BatchSTLinkFlasher.exe`.

## GitHub Actions

CI runs on push/PR (`.github/workflows/ci.yml`):

- install package + dev deps
- `pytest --cov` with **fail-under 85%**
- ruff check (non-blocking)

## Branding / icons

Flat chip logo lives under `src/batch_stlink_flasher/assets/`:

- `logo.png` / `app_icon.png` — UI splash & About
- `app_icon.ico` — Windows EXE / installer (multi-size)

Regenerate after design tweaks:

```powershell
.\.venv\Scripts\python scripts\generate_app_icon.py
```

## Versioning & build numbers

Source of truth: `packaging/version.json` (`major.minor.patch.build`).

Every packaging build increments **build** automatically:

```powershell
powershell -File scripts\build_windows.ps1          # bumps 0.1.0.N -> 0.1.0.N+1
powershell -File scripts\build_windows.ps1 -NoBump  # keep current version
powershell -File scripts\bump_version.ps1 -Patch    # 0.1.0.x -> 0.1.1.0
```

`bump_version.ps1` also syncs:

- `src/batch_stlink_flasher/_version.py`
- `pyproject.toml`
- `packaging/installer.iss`

## Versioning notes

Package/display version uses four components, e.g. `0.1.0.12` (see `packaging/version.json` and `CHANGELOG.md` for release notes).
