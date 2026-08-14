# Packaging & installer

Primary docs for *how to build* live in **[scripts/README.md](../scripts/README.md)**.

## Recommended build pipeline (3 steps)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_build_deps.ps1 -InstallSystemDeps
powershell -ExecutionPolicy Bypass -File scripts\build_app.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -ZipPortable
```

Or all at once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_all.ps1 -ZipPortable -InstallSystemDeps
```

| Step | Script | Output |
|------|--------|--------|
| 1 | `install_build_deps.ps1` | `.venv`, OpenOCD under `vendor\runtime\` |
| 2 | `build_app.ps1` | `dist\BatchSTLinkFlasher\` (EXE + Qt) |
| 3 | `build_installer.ps1` | OpenOCD bundled + optional `Setup.exe` / zip |

## Inno Setup (Setup.exe)

`build_installer.ps1` looks for `ISCC.exe` under Program Files / LocalAppData.
If missing, it **skips Setup.exe** (yellow warning) but still:

- Bundles OpenOCD into `dist\BatchSTLinkFlasher\tools\openocd`
- Can write a portable zip with `-ZipPortable`

Install [Inno Setup 6](https://jrsoftware.org/isdl.php), then re-run step 3 to produce
`dist\BatchSTLinkFlasher-<version>-Setup.exe`.

## Operator runtime (what the packaged app ships)

| Dependency | How it is provided |
|------------|--------------------|
| **Python** | Embedded inside `BatchSTLinkFlasher.exe` by PyInstaller — operators do **not** install Python |
| **OpenOCD** | Bundled under `tools\openocd\` by `build_installer.ps1` |
| **VC++ runtime** | Optional on build PC via `-InstallSystemDeps` |
| **ST-Link USB driver** | Optional; Windows PnP discovery works with ST’s official driver if present |

Pinned OpenOCD download: `packaging/runtime-deps.json` (xPack OpenOCD).

## Install on a PC (after step 3)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -DesktopShortcut -Force
```

Uninstall:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
```

## GitHub Actions

### CI (`.github/workflows/ci.yml`)

Runs on push/PR: install package + tests (coverage ≥ 85%).

### Release (`.github/workflows/release.yml`)

Triggered by tag **`vMAJOR.MINOR.PATCH`** (example: `v0.1.0`):

1. `install_build_deps.ps1`
2. `build_app.ps1 -NoBump`
3. `build_installer.ps1 -ZipPortable` (+ Inno Setup on the runner)
4. Publishes GitHub Release artifacts

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_release_tag.ps1 -Version 0.1.0 -Commit -Push
```

## Branding / icons

```powershell
.\.venv\Scripts\python scripts\generate_app_icon.py
```

See `scripts/README.md` for asset names.

## Versioning & build numbers

Source of truth: `packaging/version.json` (`major.minor.patch.build`).

```powershell
powershell -File scripts\build_app.ps1          # bumps 0.1.0.N -> 0.1.0.N+1
powershell -File scripts\build_app.ps1 -NoBump  # keep current version
powershell -File scripts\bump_version.ps1 -Patch
```
