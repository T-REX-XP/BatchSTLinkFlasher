# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Dark / light appearance with View → Theme (default: follow system)
- Script pipeline docs in `scripts/README.md`
- GitHub Release workflow on tags ``vMAJOR.MINOR.PATCH`` (e.g. ``v0.1.0``) + ``scripts/create_release_tag.ps1``
- Full installer build via ``scripts/build_installer.ps1`` (app + bundled OpenOCD + Setup.exe)
- Runtime dependency fetch `scripts/fetch_runtime_deps.ps1` / `packaging/runtime-deps.json`
- Auto-detect bundled OpenOCD under `tools/openocd` via `bundled-tools.json`
- Flat chip logo / multi-size Windows ``app_icon.ico`` (regenerate via ``scripts/generate_app_icon.py``)
- Modern Windows 11 Fluent-style app icon (gradient plate, layered chip glyph)
- Themed dark UI with button icons, splash artwork, and application icon
- About dialog (Help → About) showing version/build and project summary
- Startup splash screen that scans for ST-Link devices before opening the main window
- Auto-incrementing build number on every Windows package build (`packaging/version.json`)
- Windows installer scripts: `scripts/install.ps1`, `scripts/uninstall.ps1`, `scripts/build_installer.ps1`
- Inno Setup project `packaging/installer.iss` for Setup.exe builds

### Fixed

- Transparent About/splash logo (chip only); Windows ``app_icon`` keeps Fluent dark plate
- List both ST-Link clones when Windows assigns a generated instance id (``5&…``) because they share serial ``%``
- Splash→main handoff: show main before closing splash; avoid quit-on-last-window-closed race
- Frozen EXE ignored visible UI when ``QT_QPA_PLATFORM=offscreen`` was inherited from a test shell; clear it when frozen
- Taskbar / Alt+Tab showed the Python host icon when running from source; set Windows AppUserModelID + window icon early
- ST-Link discovery: use Config Manager presence (``DN_STARTED``) instead of unreliable ``Control`` registry key
- Root-cause: ST-Link discovery no longer spawns PowerShell (registry PnP); hides leftover console tools
- Hide PowerShell / console flash during Windows ST-Link discovery and OpenOCD jobs

### Changed

- Removed deprecated script aliases (`bootstrap`, `build_windows`, `build_full_installer`); use the 3-step pipeline in `scripts/README.md`
- Packaging scripts split into 3 steps: `install_build_deps` → `build_app` → `build_installer` (see `scripts/README.md`)
- Packaging docs: OpenOCD is bundled by the full installer; operators do not need system Python

## [0.1.0] - 2026-08-14

### Added

- Desktop UI (PySide6): device table, config, flash/cancel, live logs, summary bar
- Session log export (text / JSON) from the UI
- Coarse OpenOCD progress parsing shown in the device table
- Parallel flash orchestrator with isolated per-device failures
- Headless CLIs: `discover`, `flash` (`--all` / `--adapters` / `--dry-run`)
- Device discovery via `st-info`, Windows PnP (official ST driver), and pyusb fallback
- HLA serial normalization for OpenOCD multi-adapter binding
- Clone ST-Link placeholder serial (`%`) detection (`multi_adapter_ok=false`)
- Settings persistence (OpenOCD/firmware/target paths)
- Bootstrap installer `scripts/bootstrap.ps1` and Windows PyInstaller build `scripts/build_windows.ps1`
- GitHub Actions CI with pytest coverage gate (85%)
- Docs: requirements, architecture, plan, OpenOCD integration, packaging
