# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

### Changed

### Fixed

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
