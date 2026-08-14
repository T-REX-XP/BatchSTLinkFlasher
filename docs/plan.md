# Implementation plan

Use this checklist in order. Check items off in PRs / commits. Update `CHANGELOG.md` when a phase becomes usable.

## Phase 0 — Repo & docs (done by scaffolding)

- [x] AI-ready `docs/requirements.md`
- [x] `docs/architecture.md`, `docs/plan.md`, `docs/openocd-integration.md`
- [x] `docs/dual-flash-strategy.md`
- [x] `README.md`, `AGENTS.md`, `CHANGELOG.md`
- [x] Python package skeleton under `src/batch_stlink_flasher/`
- [x] `.gitignore`, `pyproject.toml`

## Phase 1 — Models & OpenOCD CLI builder

- [x] Implement `flashing/models.py` (`AdapterInfo`, `FlashConfig`, `JobState`, `OpenOcdPorts`)
- [x] Implement `flashing/openocd.py`: build argv list from config + serial + ports
- [x] Implement `util/ports.py`: allocate N free localhost ports
- [x] Unit tests: command builder for `.elf` / `.hex` / `.bin` (+ address)
- [ ] Manual: run generated command once from a shell against one ST-Link (operator)

**Done when**: a known-good OpenOCD command can be produced without UI.

## Phase 2 — Device discovery

- [x] `services/device_service.py`: prefer `st-info --probe` parse; fallback pyusb VID `0x0483`
- [x] Normalize HLA serial for OpenOCD (document format in openocd-integration)
- [x] CLI smoke: `python -m batch_stlink_flasher.discover` prints adapters
- [x] Unit tests with fixture stdout from `st-info`
- [ ] Manual: run discover on a PC with ≥1 ST-Link plugged in (operator)

**Done when**: connected probes list with serials on a real machine.

## Phase 3 — Single-device flash job

- [x] `FlashJob`: start process, stream lines, map exit → Succeeded/Failed/Cancelled
- [x] Soft timeout + kill
- [x] Headless CLI: `python -m batch_stlink_flasher.flash`
- [ ] Manual: flash a real target once with OpenOCD installed (operator)

**Done when**: one device flashes reliably from code (no UI).

## Phase 4 — Orchestrator (HLA parallel + clone sequential)

- [x] `FlashOrchestrator`: N jobs, unique ports, aggregate summary
- [x] Dual strategy: HLA-bound parallel; unbound clones sequential + Windows PnP isolation
- [x] Cancel all / cancel one
- [x] Ensure one failed job does not abort siblings
- [x] CLI: `python -m batch_stlink_flasher.flash --all` / `--adapters 1,2`
- [ ] Manual: flash 2+ probes (HLA parallel and/or clone sequential) on hardware (operator)

**Done when**: multi-adapter flash works from a small script for both probe types.

## Phase 5 — Desktop UI

- [x] Main window layout per `FR-UX-01`
- [x] Wire discovery refresh, config panel, start/cancel
- [x] Per-device status + log view
- [x] USB port/hub column; Identify LED (`FR-DISC-07`)
- [x] Validation before Start (`FR-UX-02`)
- [x] Settings persistence
- [ ] Manual: run UI against real ST-Link + OpenOCD (operator)

**Done when**: acceptance criteria in `docs/requirements.md` §7 pass.

## Phase 6 — Polish

- [x] Log export (text / JSON)
- [x] Better progress parsing (OpenOCD stage / % heuristics)
- [x] Packaging notes / PyInstaller recipe (`docs/packaging.md`, `scripts/build_app.ps1`)
- [x] Tag version `0.1.0` in `CHANGELOG.md` / package metadata
- [x] Build scripts to prepare dist
- [x] GitHub Actions CI pipeline
- [x] Test coverage gate minimum 85%
- [x] Autoinstaller / bootstrap script for dependencies + docs pointers
- [x] Windows end-user installer (`scripts/install.ps1`) + uninstaller + Inno Setup script

## Suggested commit style

- `docs: …` for documentation-only
- `feat: …` for user-visible capability
- `fix: …` for bugs
- `test: …` / `chore: …` as appropriate

Keep commits small and aligned to one phase item when possible.
