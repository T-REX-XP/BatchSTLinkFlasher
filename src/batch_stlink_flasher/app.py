"""Application bootstrap."""

from __future__ import annotations

import sys

from batch_stlink_flasher import __version__


def run() -> int:
    """
    Start the Qt application.

    UI lands in Phase 5 (see docs/plan.md). Until then, print status and exit.
    """
    print(
        f"Batch ST-Link Flasher {__version__}\n"
        "\n"
        "Desktop UI is not implemented yet (Phase 5).\n"
        "What works now:\n"
        "  pytest\n"
        "  python -m batch_stlink_flasher.discover\n"
        "  python -m batch_stlink_flasher.flash --firmware FILE --target CFG [--all]\n"
        "\n"
        "Next: Phase 5 (desktop UI) - see docs/plan.md\n",
        file=sys.stderr,
    )
    return 2
