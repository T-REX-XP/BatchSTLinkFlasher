# Scripts — Batch ST-Link Flasher

Recommended packaging pipeline on Windows (three clear steps):

| Step | Script | Purpose |
|------|--------|---------|
| **1** | [`install_build_deps.ps1`](install_build_deps.ps1) | Install *build* dependencies (Python venv, pip extras, OpenOCD download, optional winget tools) |
| **2** | [`build_app.ps1`](build_app.ps1) | Build the GUI app with PyInstaller → `dist\BatchSTLinkFlasher\` |
| **3** | [`build_installer.ps1`](build_installer.ps1) | Bundle OpenOCD into that folder and produce `Setup.exe` / portable zip |

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_build_deps.ps1 -InstallSystemDeps
powershell -ExecutionPolicy Bypass -File scripts\build_app.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -ZipPortable
```

One-shot convenience (runs 1 → 2 → 3):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_all.ps1 -ZipPortable -InstallSystemDeps
```

## Why this split?

- **Build deps ≠ operator runtime.** Operators get a frozen EXE (Python embedded) + bundled OpenOCD. Developers need Python/PyInstaller on the build PC.
- **App build ≠ installer.** You can iterate on the app (`build_app.ps1`) without recompiling Setup.exe every time.
- **Installer assumes a built app.** Step 3 only packages what step 2 produced (plus OpenOCD).

## Step details

### 1 — `install_build_deps.ps1`

Installs what the *build machine* needs:

- Python 3.11+ (optional `-InstallSystemDeps` via winget)
- `.venv` with `.[dev,packaging]` (PySide6, pytest, PyInstaller, …)
- OpenOCD archive under `vendor\runtime\openocd\` (for bundling in step 3)
- Checks for Inno Setup (`ISCC.exe`) used in step 3

Useful switches: `-InstallSystemDeps`, `-SkipOpenOcd`, `-SkipTests`, `-DevOnly`

### 2 — `build_app.ps1`

Runs PyInstaller (windowed onedir):

- Output: `dist\BatchSTLinkFlasher\BatchSTLinkFlasher.exe`
- Bumps `packaging/version.json` build number unless `-NoBump`
- Does **not** create Setup.exe

### 3 — `build_installer.ps1`

Packages the existing `dist\BatchSTLinkFlasher\` folder:

- Copies OpenOCD → `dist\BatchSTLinkFlasher\tools\openocd\`
- Writes `bundled-tools.json` so the app auto-finds OpenOCD
- Optional portable zip (`-ZipPortable`)
- Optional Inno Setup `Setup.exe` (needs [Inno Setup 6](https://jrsoftware.org/isinfo.php))

Useful switches: `-BuildApp`, `-FetchOpenOcd`, `-SkipOpenOcd`, `-ZipPortable`, `-SkipInno`, `-NoBump`

## Operator install (after step 3)

These install a *built* payload on a PC (not for compiling the project):

| Script | Purpose |
|--------|---------|
| [`install.ps1`](install.ps1) | Copy `dist\…` to Program Files / LocalAppData, shortcuts, Add/Remove Programs |
| [`uninstall.ps1`](uninstall.ps1) | Remove that install |

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -DesktopShortcut -Force
```

## Other helpers

| Script | Purpose |
|--------|---------|
| [`fetch_runtime_deps.ps1`](fetch_runtime_deps.ps1) | Download/verify OpenOCD only |
| [`bump_version.ps1`](bump_version.ps1) / [`version.ps1`](version.ps1) | Version helpers |
| [`create_release_tag.ps1`](create_release_tag.ps1) | Create `vMAJOR.MINOR.PATCH` tag → GitHub Release workflow |
| [`generate_app_icon.py`](generate_app_icon.py) | Regenerate Fluent app icons |

## Deprecated aliases

Kept so old docs/CI keep working; they print a note and forward:

| Old | Prefer |
|-----|--------|
| `bootstrap.ps1` | `install_build_deps.ps1` |
| `build_windows.ps1` | `build_app.ps1` |
| `build_full_installer.ps1` | `build_all.ps1` |

## Artifacts

After a full pipeline:

```
dist\
  BatchSTLinkFlasher\                 # runnable onedir (app + tools\openocd)
  BatchSTLinkFlasher-x.y.z.b-portable.zip
  BatchSTLinkFlasher-x.y.z.b-Setup.exe   # if Inno Setup installed
vendor\runtime\openocd\               # cached OpenOCD used by step 3
```

## See also

- [docs/packaging.md](../docs/packaging.md) — packaging overview & release tags
- [docs/openocd-integration.md](../docs/openocd-integration.md) — OpenOCD usage
