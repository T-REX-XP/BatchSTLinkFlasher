"""Export session logs to text or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SessionLog:
    """In-memory flash session log for export."""

    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    lines: list[str] = field(default_factory=list)
    results: list[dict[str, str]] = field(default_factory=list)

    def append(self, line: str) -> None:
        self.lines.append(line)

    def add_result(self, serial: str, state: str, error: str = "") -> None:
        self.results.append({"serial": serial, "state": state, "error": error})


def export_log_text(path: Path, session: SessionLog) -> None:
    """Write a plain-text session log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(session.lines)
    if not body.endswith("\n") and body:
        body += "\n"
    header = f"# Batch ST-Link Flasher session\n# started: {session.started_at}\n\n"
    path.write_text(header + body, encoding="utf-8")


def export_log_json(path: Path, session: SessionLog) -> None:
    """Write a JSON session log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(session)
    payload["exported_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
