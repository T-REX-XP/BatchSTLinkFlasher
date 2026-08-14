"""Windows packaging notes for Batch ST-Link Flasher."""

# Packaging

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

Distribute that folder. Operators still need OpenOCD installed.

Alternate: `packaging\batch_stlink_flasher.spec` (paths relative to `packaging/`).

## GitHub Actions

CI runs on push/PR (`.github/workflows/ci.yml`):

- install package + dev deps
- `pytest --cov` with **fail-under 85%**
- ruff check (non-blocking style gate can be tightened later)

## Versioning

Package version is `0.1.0` (see `pyproject.toml` and `CHANGELOG.md`).
