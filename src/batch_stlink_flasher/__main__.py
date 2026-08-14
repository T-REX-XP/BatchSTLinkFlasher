"""Entry point: ``python -m batch_stlink_flasher``."""

from __future__ import annotations


def main() -> int:
    """Launch the desktop app (implement in Phase 5; stub until then)."""
    from batch_stlink_flasher.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
