# Scripts

Three-step Windows packaging → **app EXE** + **Setup.exe installer**:

| Step | Script | Output |
|------|--------|--------|
| 1 | `install_build_deps.ps1` | `.venv`, OpenOCD under `vendor\runtime\`, optional Inno Setup |
| 2 | `build_app.ps1` | `dist\BatchSTLinkFlasher\BatchSTLinkFlasher.exe` (onedir + Qt) |
| 3 | `build_installer.ps1` | Bundled OpenOCD + **`dist\…-Setup.exe`** (+ optional zip) |

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_build_deps.ps1 -InstallSystemDeps
powershell -ExecutionPolicy Bypass -File scripts\build_app.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -ZipPortable
```

If Inno Setup is missing, step 3 can auto-install it:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -InstallInno -ZipPortable
```

All three at once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_all.ps1 -ZipPortable -InstallSystemDeps -InstallInno
```

## What operators get

| Artifact | Role |
|----------|------|
| `BatchSTLinkFlasher-<ver>-Setup.exe` | **Single installer file** (preferred) |
| `BatchSTLinkFlasher-<ver>-portable.zip` | Optional zip of the onedir folder |
| `dist\BatchSTLinkFlasher\` | Built app folder (EXE + Qt + `tools\openocd`) |

The app is built as **onedir** (not PyInstaller `--onefile`) so Qt plugins and
bundled OpenOCD stay beside the EXE. Inno packs that folder into one Setup.exe.

## Setup.exe / Inno Setup

Step 3 needs [Inno Setup 6](https://jrsoftware.org/isdl.php) (`ISCC.exe`).

- `-InstallSystemDeps` on step 1 also tries `winget install JRSoftware.InnoSetup`
- `-InstallInno` on step 3 installs via winget or chocolatey if missing
- Without Inno, step 3 **fails** unless you pass `-SkipInno`

## Operator install

Prefer Setup.exe from step 3. Fallback:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -DesktopShortcut -Force
powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
```

## Other helpers

| Script | When |
|--------|------|
| `fetch_runtime_deps.ps1` | Download OpenOCD only |
| `bump_version.ps1` / `version.ps1` | Version helpers (syncs `installer.iss`) |
| `create_release_tag.ps1` | Tag `vMAJOR.MINOR.PATCH` for GitHub Release |
| `generate_app_icon.py` | Regenerate app icons |

PyInstaller spec: `packaging/batch_stlink_flasher.spec`  
Inno script: `packaging/installer.iss`

See also: [docs/packaging.md](../docs/packaging.md)
