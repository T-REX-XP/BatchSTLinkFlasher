"""Entry point: ``python -m batch_stlink_flasher``."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Launch the desktop app, or run a headless Identify LED job."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--identify-blink":
        if len(args) < 2:
            print("usage: --identify-blink <job.json>", file=sys.stderr)
            return 2
        from batch_stlink_flasher.services.identify import run_identify_blink_job

        return run_identify_blink_job(args[1])

    from batch_stlink_flasher.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
