# Batch ST-Link Flasher

Desktop app to flash the **same firmware** onto **multiple STM32 targets in parallel**, each via its own **ST-Link V2** programmer, driven by **OpenOCD**.

**Version:** 0.1.0

## Status

| Phase | Status |
|-------|--------|
| 0 Docs + skeleton | Done |
| 1 Models + OpenOCD argv | Done |
| 2 Device discovery | Done |
| 3 Single-device flash | Done |
| 4 Parallel orchestrator | Done |
| 5 Desktop UI | Done |
| 6 Polish | Done |

See `docs/plan.md`.

## Docs

| Document | Description |
|----------|-------------|
| [docs/requirements.md](docs/requirements.md) | Product requirements (AI-ready) |
| [docs/architecture.md](docs/architecture.md) | Design & module layout |
| [docs/plan.md](docs/plan.md) | Phased implementation checklist |
| [docs/openocd-integration.md](docs/openocd-integration.md) | OpenOCD multi-adapter notes |
| [docs/packaging.md](docs/packaging.md) | Bootstrap, PyInstaller, CI |
| [AGENTS.md](AGENTS.md) | Rules for AI agents |
| [CHANGELOG.md](CHANGELOG.md) | Change history |

## Prerequisites

- Windows 10/11 (primary)
- Python 3.11+
- [OpenOCD](https://openocd.org/) on `PATH` (or set in the UI)
- Optional: [stlink](https://github.com/stlink-org/stlink) (`st-info`) for probe listing
- One or more ST-Link V2 / V2-1 programmers with targets powered and wired

## Quick install (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
.\.venv\Scripts\activate
python -m batch_stlink_flasher
```

## Manual setup

```bash
cd BatchSTLinkFlasher
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m batch_stlink_flasher.discover
python -m batch_stlink_flasher.flash --firmware app.elf --target target/stm32f1x.cfg --dry-run
python -m batch_stlink_flasher
```

Parallel flashing needs unique HLA serials on each probe; a single clone with serial `%` still works alone.

Shortcuts: **Ctrl+Return** flash, **Esc** cancel, **Ctrl+S** export log, **F5** refresh.

## Build distributable

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

See [docs/packaging.md](docs/packaging.md).

## Operator flow

1. Plug in 1–N ST-Links; refresh device list.
2. Select firmware (`.elf` / `.hex` / `.bin`).
3. Choose OpenOCD interface + target scripts.
4. Select devices → **Flash**.
5. Watch per-device progress and logs; export or cancel if needed.

## License

MIT
