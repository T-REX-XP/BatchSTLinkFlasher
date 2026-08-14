# AGENTS.md — working in this repository

This project is designed for AI-assisted implementation. Follow these rules.

## Source of truth

1. `docs/requirements.md` — product contract (IDs like `FR-*`, `NFR-*`).
2. `docs/architecture.md` — modules and threading.
3. `docs/plan.md` — implement phases in order; do not skip to UI before Phase 3 works.
4. `docs/openocd-integration.md` — OpenOCD CLI behavior.
5. `CHANGELOG.md` — update under **Unreleased** when user-visible behavior changes.

If chat disagrees with these docs, **update the docs first** (or ask the user), then code.

## Stack (do not change casually)

- Python 3.11+, package `batch_stlink_flasher` under `src/`
- UI: PySide6
- Flasher backend: OpenOCD subprocesses (one per adapter)

## Implementation rules

- Keep the UI thread free of blocking OpenOCD/USB work.
- One OpenOCD process per selected adapter; unique TCP ports; always bind serial.
- Prefer small, testable modules (`openocd.py` command builder must be unit-tested).
- Do not commit secrets, local firmware binaries, or machine-specific absolute paths in tracked config.
- Do not expand scope beyond the current `docs/plan.md` phase unless the user asks.

## Commands (once deps installed)

```bash
pip install -e ".[dev]"
pytest
python -m batch_stlink_flasher
```

Coverage must stay ≥ **85%** (`--cov-fail-under=85`). Build deps: `scripts/install_build_deps.ps1`. Packaging steps: `scripts/README.md`.

Release tags use `vMAJOR.MINOR.PATCH` (e.g. `v0.1.0`); see `scripts/create_release_tag.ps1` and `.github/workflows/release.yml`.

## When stuck

Document the blocker in the PR/commit message and in **Unreleased** notes if it changes operator expectations. Prefer fixing discovery/serial encoding with a real probe before guessing UI workarounds.
