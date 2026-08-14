"""Unit tests for session log export."""

from __future__ import annotations

import json
from pathlib import Path

from batch_stlink_flasher.util.log_export import SessionLog, export_log_json, export_log_text


def test_export_log_text(tmp_path: Path) -> None:
    session = SessionLog()
    session.append("line1")
    session.append("line2")
    path = tmp_path / "out.log"
    export_log_text(path, session)
    text = path.read_text(encoding="utf-8")
    assert "line1" in text
    assert "line2" in text
    assert "started:" in text


def test_export_log_json(tmp_path: Path) -> None:
    session = SessionLog()
    session.append("hello")
    session.add_result("A", "succeeded")
    path = tmp_path / "out.json"
    export_log_json(path, session)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["lines"] == ["hello"]
    assert payload["results"][0]["serial"] == "A"
    assert "exported_at" in payload
