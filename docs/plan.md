# Implementation plan

Use this checklist in order. Check items off in PRs / commits. Update `CHANGELOG.md` when a phase becomes usable.

## Phase 0 — Repo & docs (done by scaffolding)

- [x] AI-ready `docs/requirements.md`
- [x] `docs/architecture.md`, `docs/plan.md`, `docs/openocd-integration.md`
- [x] `README.md`, `AGENTS.md`, `CHANGELOG.md`
- [x] Python package skeleton under `src/batch_stlink_flasher/`
- [x] `.gitignore`, `pyproject.toml`

## Phase 1 — Models & OpenOCD CLI builder

**Owner: implementer (you / agent)**

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

## Phase 4 — Parallel orchestrator

- [x] `FlashOrchestrator`: N jobs, unique ports, aggregate summary
- [x] Cancel all / cancel one
- [x] Ensure one failed job does not abort siblings
- [x] CLI: `python -m batch_stlink_flasher.flash --all` / `--adapters 1,2`
- [ ] Manual: flash 2+ probes in parallel on hardware (operator)

**Done when**: 2+ devices flash in parallel from a small script.

## Phase 5 — Desktop UI

- [ ] Main window layout per `FR-UX-01`
- [ ] Wire discovery refresh, config panel, start/cancel
- [ ] Per-device status + log view
- [ ] Validation before Start (`FR-UX-02`)
- [ ] Settings persistence

**Done when**: acceptance criteria in `docs/requirements.md` §7 pass.

## Phase 6 — Polish

- [ ] Log export
- [ ] Better progress parsing (if OpenOCD output allows)
- [ ] Packaging notes / PyInstaller recipe in README
- [ ] Tag version `0.1.0` in `CHANGELOG.md`

## Suggested commit style

- `docs: …` for documentation-only
- `feat: …` for user-visible capability
- `fix: …` for bugs
- `test: …` / `chore: …` as appropriate

Keep commits small and aligned to one phase item when possible.



implement build scripts to prepare dist
implement github pipelines
test coverage must be minimum 85%
Implement autoinstaller script for the dependencies and documentation
