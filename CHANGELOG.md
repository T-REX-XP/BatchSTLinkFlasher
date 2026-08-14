# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Phase 5: PySide6 desktop UI (device table, config, flash/cancel, live logs, summary)
- Phase 5: QSettings persistence for OpenOCD/firmware/target paths
- Phase 4: `FlashOrchestrator` for parallel multi-adapter flashing (isolated failures)
- Phase 4: CLI `--all` / `--adapters` for batch flash
- Phase 3: `FlashJob` with streamed OpenOCD logs, timeout, and cancel
- Phase 3: CLI `python -m batch_stlink_flasher.flash` (supports `--dry-run`)
- OpenOCD command builder omits `hla_serial` when adapter has no usable serial (clone `%`)
- Phase 2: ST-Link discovery via `st-info --probe` with Windows PnP + pyusb fallbacks
- Phase 2: HLA serial normalization (`util/hla_serial.py`) for OpenOCD
- Phase 2: CLI `python -m batch_stlink_flasher.discover`
- Windows PnP discovery works with the official ST driver (fixes pyusb “No backend available”)
- Detect clone ST-Links with placeholder USB serial (`%`) and flag `multi_adapter_ok=false`
- Phase 1: models, OpenOCD argv builder, port allocation
- Unit tests including offscreen UI smoke tests
- Docs under `docs/`, `AGENTS.md`, package skeleton
