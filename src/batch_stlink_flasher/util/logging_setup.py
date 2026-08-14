"""Logging configuration helpers."""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.WARNING) -> None:
    """Configure root logging once for CLI entry points."""
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
