"""Parse coarse flash progress from OpenOCD log lines."""

from __future__ import annotations

import re
from dataclasses import dataclass

_PERCENT = re.compile(r"(\d{1,3})\s*%")
_STAGE_RULES: list[tuple[re.Pattern[str], str, int]] = [
    (re.compile(r"Programming Started", re.I), "programming", 20),
    (re.compile(r"Programming Finished", re.I), "programmed", 70),
    (re.compile(r"Verify Started", re.I), "verifying", 80),
    (re.compile(r"Verified OK|Verify Finished", re.I), "verified", 95),
    (re.compile(r"shutdown command invoked", re.I), "done", 100),
    (re.compile(r"wrote\s+\d+\s+bytes", re.I), "writing", 50),
    (re.compile(r"target halted", re.I), "halted", 15),
    (re.compile(r"Unable to match|Error:", re.I), "error", 0),
]


@dataclass(frozen=True)
class ProgressUpdate:
    """Best-effort progress derived from one OpenOCD line."""

    stage: str
    percent: int | None
    label: str


def parse_openocd_progress(line: str) -> ProgressUpdate | None:
    """
    Extract a progress hint from an OpenOCD stdout/stderr line.

    Returns ``None`` when the line carries no useful progress signal.
    """
    text = line.strip()
    if not text:
        return None

    for pattern, stage, percent in _STAGE_RULES:
        if pattern.search(text):
            return ProgressUpdate(stage=stage, percent=percent, label=f"{stage} ({percent}%)")

    match = _PERCENT.search(text)
    if match:
        value = min(100, max(0, int(match.group(1))))
        return ProgressUpdate(stage="progress", percent=value, label=f"{value}%")

    return None
