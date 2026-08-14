"""Unit tests for OpenOCD progress parsing."""

from __future__ import annotations

from batch_stlink_flasher.util.progress import parse_openocd_progress


def test_parse_programming_started() -> None:
    update = parse_openocd_progress("** Programming Started **")
    assert update is not None
    assert update.stage == "programming"
    assert update.percent == 20


def test_parse_percent() -> None:
    update = parse_openocd_progress("Progress: 42%")
    assert update is not None
    assert update.percent == 42


def test_parse_ignore_noise() -> None:
    assert parse_openocd_progress("Info : clock speed 1000 kHz") is None
