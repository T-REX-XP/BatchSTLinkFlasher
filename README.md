# Batch ST-Link Flasher

Desktop app to flash the **same firmware** onto **multiple STM32 targets in parallel**, each via its own **ST-Link V2** programmer, driven by **OpenOCD**.

## Status

| Phase | Status |
|-------|--------|
| 0 Docs + skeleton | Done |
| 1 Models + OpenOCD argv | Done |
| 2 Device discovery | Done (`discover` CLI) |
| 3–4 Flash jobs | Not started |
| 5 Desktop UI | Not started |
| 6 Polish | Not started |

See `docs/plan.md`.

## Docs

| Document | Description |
|----------|-------------|
| [docs/requirements.md](docs/requirements.md) | Product requirements (AI-ready) |
| [docs/architecture.md](docs/architecture.md) | Design & module layout |
| [docs/plan.md](docs/plan.md) | Phased implementation checklist |
| [docs/openocd-integration.md](docs/openocd-integration.md) | OpenOCD multi-adapter notes |
| [AGENTS.md](AGENTS.md) | Rules for AI agents |
| [CHANGELOG.md](CHANGELOG.md) | Change history |

## Prerequisites

- Windows 10/11 (primary)
- Python 3.11+
- [OpenOCD](https://openocd.org/) on `PATH` (needed from Phase 3 onward)
- Optional: [stlink](https://github.com/stlink-org/stlink) (`st-info`) for probe listing
- One or more ST-Link V2 / V2-1 programmers with targets powered and wired

## Setup

```bash
cd BatchSTLinkFlasher
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
python -m batch_stlink_flasher.discover   # list ST-Links (works now)
```

`python -m batch_stlink_flasher` launches the UI — that arrives in **Phase 5**.

## Operator flow (target UX)

1. Plug in 1–N ST-Links; refresh device list.
2. Select firmware (`.elf` / `.hex` / `.bin`).
3. Choose OpenOCD interface + target scripts.
4. Select devices → **Flash**.
5. Watch per-device progress and logs; cancel if needed.

## License

TBD
