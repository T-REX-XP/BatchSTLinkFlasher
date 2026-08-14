# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Phase 1: `AdapterInfo`, `FlashConfig`, `JobState`, `OpenOcdPorts` models
- Phase 1: OpenOCD argv builder (`build_openocd_command`) for `.elf` / `.hex` / `.bin`
- Phase 1: free TCP port allocation helpers for parallel OpenOCD instances
- Unit tests for models, OpenOCD command building, and port allocation
- AI-ready requirements, architecture, plan, and OpenOCD integration docs under `docs/`
- `AGENTS.md` for agent workflow
- Python package skeleton `src/batch_stlink_flasher/` and `pyproject.toml`
- Initial `README.md` and repository layout
