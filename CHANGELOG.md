# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Settings dialog (Edit → Settings / toolbar): OpenOCD path, interface, scripts ``-s``, timeout, theme
- Docs: ``docs/stlink-clone-serial.md`` — ST-Link V2 clone USB serial conflicts, recovery approaches, and community repos (from ``docs/stlink.pdf`` notes)
- Device table shows USB port / hub (from Windows ``LocationInformation``)
- Dual flash strategy: HLA originals flash in parallel; clones flash sequentially with Windows USB isolation
- Docs: ``docs/dual-flash-strategy.md`` (flow / sequence / isolation diagrams)
- Dark / light appearance with View → Theme (default: follow system)
- About dialog (Help → About) showing version/build and project summary
- Startup splash that scans for ST-Links before the main window
- GitHub Release workflow on tags ``vMAJOR.MINOR.PATCH`` + ``scripts/create_release_tag.ps1``
- Three-step packaging: ``install_build_deps`` → ``build_app`` → ``build_installer`` (bundled OpenOCD, optional Setup.exe / zip)
- Runtime dependency fetch ``scripts/fetch_runtime_deps.ps1`` / ``packaging/runtime-deps.json``
- Auto-detect bundled OpenOCD under ``tools/openocd`` via ``bundled-tools.json``
- Fluent chip app logo / multi-size ``app_icon.ico`` (``scripts/generate_app_icon.py``)
- Auto-incrementing build number on each ``build_app.ps1`` run (``packaging/version.json``)

### Fixed

- Theme combo / ``QComboBox``: restore visible drop-down arrow (stylesheet was blanking Fusion’s indicator)
- Browse ``…`` buttons: shared ``path_browse_row`` + identical ``#browseButton`` chrome on main window and Settings
- Config form overlap: config is no longer a 3-way splitter pane (devices|bottom with fixed-height form + log); OpenOCD summary stays in the status bar; legacy splitter state discarded
- Closing while a flash is running asks for confirmation before cancelling jobs and quitting
- Browse dialogs use shared file masks (firmware ``*.elf/hex/bin``, OpenOCD ``openocd.exe``, configs ``*.cfg``, log export)
- Browse buttons: Windows-style ``…`` ellipsis controls (no folder icons / custom glyphs)
- Dark theme: Settings / dialogs no longer show white panes with light-on-light labels (Fusion QPalette + tab/combo styles)
- List both ST-Link clones when Windows assigns a generated instance id (``5&…``) because they share serial ``%``
- Splash→main handoff: show main before closing splash; avoid quit-on-last-window-closed race
- Frozen EXE ignored visible UI when ``QT_QPA_PLATFORM=offscreen`` was inherited from a test shell
- Taskbar / Alt+Tab showed the Python host icon when running from source (AppUserModelID + early window icon)
- ST-Link discovery: Config Manager presence (``DN_STARTED``); no PowerShell console flash
- Corrupt multi-size ``app_icon.ico`` (Pillow writer) that made Setup.exe / Explorer icons look broken
- Installer wizard now uses branded sidebar / small images alongside ``SetupIconFile``

### Changed

- CI/Release workflows: bump to Node 24 actions (``checkout@v5``, ``setup-python@v6``, ``action-gh-release@v3``)
- Packaging: Setup.exe is required by default (``build_installer.ps1``); ``-InstallInno`` / ``-InstallSystemDeps`` can install Inno Setup; app build uses ``packaging/batch_stlink_flasher.spec``
- README redesigned with badges, feature summary, and screenshot under ``docs/imgs/``
- Documentation synced with current product (README, requirements, architecture, plan, packaging, scripts)
- App logo: Windows 11 Fluent chip mark with transparent corners (shared by EXE, About, Setup.exe)
- Compact laptop-friendly UI: devices/log splitter with fixed-height flash config,
  interactive device columns (hide PID/HLA when narrow), Settings dialog for tool prefs,
  persisted window/splitter/column layout (View → Reset layout)
- Main config panel keeps firmware / target / BIN base; OpenOCD path, interface, scripts, timeout, and theme moved to Settings
- Removed deprecated script aliases (``bootstrap``, ``build_windows``, ``build_full_installer``)
- Packaging: OpenOCD bundled by ``build_installer.ps1``; ``Setup.exe`` skipped gracefully if Inno Setup is not installed

## [0.1.0] - 2026-08-14

### Added

- Desktop UI (PySide6): device table, config, flash/cancel, live logs, summary bar
- Session log export (text / JSON) from the UI
- Coarse OpenOCD progress parsing shown in the device table
- Parallel flash orchestrator with isolated per-device failures
- Headless CLIs: ``discover``, ``flash`` (``--all`` / ``--adapters`` / ``--dry-run``)
- Device discovery via ``st-info``, Windows PnP (official ST driver), and pyusb fallback
- HLA serial normalization for OpenOCD multi-adapter binding
- Clone ST-Link placeholder serial (``%``) detection (``multi_adapter_ok=false``)
- Settings persistence (OpenOCD/firmware/target paths)
- GitHub Actions CI with pytest coverage gate (85%)
- Docs: requirements, architecture, plan, OpenOCD integration, packaging
