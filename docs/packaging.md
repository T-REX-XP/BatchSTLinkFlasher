# Packaging & installer

## Operator runtime dependencies

| Dependency | How it is provided |
|------------|--------------------|
| **Python** | Embedded inside `BatchSTLinkFlasher.exe` by PyInstaller — **operators do not install Python** |
| **OpenOCD** | Bundled under `tools\openocd\` when you use the full installer build |
| **VC++ runtime** | Optional; install with winget via `-InstallSystemDeps` on the build PC |
| **ST-Link USB driver** | Optional; Windows PnP discovery works with ST’s official driver if present |

Pinned OpenOCD download: `packaging/runtime-deps.json` (xPack OpenOCD).

## Full installer (recommended)

One script builds the app, downloads OpenOCD, stages it into the dist folder, and produces Setup.exe / portable zip:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_full_installer.ps1 -ZipPortable -InstallSystemDeps
```

What it does:

1. Ensures Python 3.11+ on the **build** machine (optional winget install)
2. Creates `.venv` and installs packaging extras
3. Downloads OpenOCD → `vendor\runtime\openocd\`
4. Builds `dist\BatchSTLinkFlasher\` (PyInstaller)
5. Copies OpenOCD → `dist\BatchSTLinkFlasher\tools\openocd\`
6. Writes `bundled-tools.json` (app auto-selects OpenOCD + scripts path)
7. Compiles Inno Setup `Setup.exe` when ISCC is available

Useful switches:

| Switch | Meaning |
|--------|---------|
| `-SkipFetch` | Reuse already-downloaded OpenOCD |
| `-SkipBuild` | Reuse existing onedir |
| `-NoBump` | Keep current version |
| `-SkipInno` | Skip Setup.exe |
| `-ZipPortable` | Also zip the onedir (includes OpenOCD) |
| `-InstallSystemDeps` | winget: VC++ redistributable (+ Python if missing for build) |
| `-SkipPythonBootstrap` | Assume `.venv` is ready |

Fetch OpenOCD alone:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\fetch_runtime_deps.ps1
```

## Dev bootstrap

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

Creates `.venv`, installs `[dev]`, runs tests, and prints docs links.

## Build Windows dist only (no OpenOCD bundle)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Output folder: `dist\BatchSTLinkFlasher\` (app only). Prefer `build_full_installer.ps1` for operator installs.

## Install on a PC

### Option A — PowerShell installer (no Inno Setup)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -Build -DesktopShortcut -Force
```

For a full tool bundle, build with `build_full_installer.ps1` first (or pass a SourceDir that already contains `tools\openocd`).

Useful switches:

| Switch | Meaning |
|--------|---------|
| `-Build` | Run PyInstaller build first (does **not** fetch OpenOCD by itself) |
| `-DesktopShortcut` | Create Desktop icon |
| `-AllUsers` | Install to Program Files (needs admin) |
| `-Force` | Overwrite without prompt |
| `-SourceDir path` | Use an existing onedir folder |

Uninstall:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
```

### Option B — Setup.exe (Inno Setup)

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Run `scripts\build_full_installer.ps1`
3. Distribute `dist\BatchSTLinkFlasher-<version>-Setup.exe`

### Option C — Portable zip

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_full_installer.ps1 -SkipInno -ZipPortable
```

Unzip and run `BatchSTLinkFlasher.exe` (OpenOCD is under `tools\openocd`).

## GitHub Actions

### CI (`.github/workflows/ci.yml`)

Runs on push/PR:

- install package + dev deps
- `pytest --cov` with **fail-under 85%**
- ruff check (non-blocking)

### Release (`.github/workflows/release.yml`)

Triggered by a SemVer tag in the form **`vMAJOR.MINOR.PATCH`** (example: `v0.1.0`):

1. Syncs `packaging/version.json` to `MAJOR.MINOR.PATCH.0`
2. Runs tests
3. Fetches OpenOCD, builds the Windows onedir, bundles tools
4. Builds portable zip + Setup.exe (Inno Setup via Chocolatey)
5. Publishes a GitHub Release with those artifacts

Create and push a release tag:

```powershell
# Sets version files, creates annotated tag v0.1.0, optionally pushes
powershell -ExecutionPolicy Bypass -File scripts\create_release_tag.ps1 -Version 0.1.0 -Commit -Push
```

Or manually:

```powershell
powershell -File scripts\bump_version.ps1 -Set 0.1.0.0
git add packaging/version.json packaging/installer.iss pyproject.toml src/batch_stlink_flasher/_version.py
git commit -m "chore: release v0.1.0"
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin HEAD
git push origin v0.1.0
```

You can also run the workflow manually (Actions → Release → Run workflow) and enter `0.1.0`.

## Branding / icons

Flat Fluent-style chip logo lives under `src/batch_stlink_flasher/assets/`:

- `app_icon_source.png` — master artwork (Windows 11 style)
- `logo.png` / `app_icon.png` — UI splash & About
- `app_icon.ico` — Windows EXE / installer (multi-size 16–256)

Regenerate after replacing the source art:

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
