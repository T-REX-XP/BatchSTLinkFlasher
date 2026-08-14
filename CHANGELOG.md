# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Phase 2: ST-Link discovery via `st-info --probe` with Windows PnP + pyusb fallbacks
- Phase 2: HLA serial normalization (`util/hla_serial.py`) for OpenOCD
- Phase 2: CLI `python -m batch_stlink_flasher.discover`
- Windows PnP discovery works with the official ST driver (fixes pyusb “No backend available”)
- Detect clone ST-Links with placeholder USB serial (`%`) and flag `multi_adapter_ok=false`
- Phase 1: `AdapterInfo`, `FlashConfig`, `JobState`, `OpenOcdPorts` models
- Phase 1: OpenOCD argv builder (`build_openocd_command`) for `.elf` / `.hex` / `.bin`
- Phase 1: free TCP port allocation helpers for parallel OpenOCD instances
- Unit tests for models, OpenOCD command building, port allocation, and discovery
- AI-ready requirements, architecture, plan, and OpenOCD integration docs under `docs/`
- `AGENTS.md` for agent workflow
- Python package skeleton `src/batch_stlink_flasher/` and `pyproject.toml`
- Initial `README.md` and repository layout
