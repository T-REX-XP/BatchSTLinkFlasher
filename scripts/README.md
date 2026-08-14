# Scripts

Three-step Windows packaging:

| Step | Script | Output |
|------|--------|--------|
| 1 | `install_build_deps.ps1` | `.venv`, OpenOCD under `vendor\runtime\` |
| 2 | `build_app.ps1` | `dist\BatchSTLinkFlasher\` |
| 3 | `build_installer.ps1` | Bundle OpenOCD + optional `Setup.exe` / zip |

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_build_deps.ps1 -InstallSystemDeps
powershell -ExecutionPolicy Bypass -File scripts\build_app.ps1
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -ZipPortable
```

All three at once: `scripts\build_all.ps1 -ZipPortable -InstallSystemDeps`

## Setup.exe / Inno Setup

Step 3 needs [Inno Setup 6](https://jrsoftware.org/isdl.php) (`ISCC.exe`) to compile
`Setup.exe`. Without it you still get a runnable `dist\BatchSTLinkFlasher\` with
bundled OpenOCD; the script prints `Setup.exe skipped`.

## Operator install

Prefer `Setup.exe` from step 3 when available. Otherwise:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -DesktopShortcut -Force
powershell -ExecutionPolicy Bypass -File scripts\uninstall.ps1
```

## Other helpers

| Script | When |
|--------|------|
| `fetch_runtime_deps.ps1` | Download OpenOCD only |
| `bump_version.ps1` / `version.ps1` | Version helpers |
| `create_release_tag.ps1` | Tag `vMAJOR.MINOR.PATCH` for GitHub Release |
| `generate_app_icon.py` | Regenerate app icons |

See also: [docs/packaging.md](../docs/packaging.md)
