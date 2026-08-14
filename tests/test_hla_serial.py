"""Tests for HLA serial normalization."""

from __future__ import annotations

import pytest

from batch_stlink_flasher.util.hla_serial import (
    bytes_to_hla_serial,
    hex_serial_to_hla,
    normalize_hla_serial,
)


def test_hex_serial_to_hla() -> None:
    assert hex_serial_to_hla("303031") == '"\\x30\\x30\\x31"'


def test_hex_serial_strips_trailing_null() -> None:
    assert hex_serial_to_hla("5400") == '"\\x54"'


def test_normalize_prefers_hla_field() -> None:
    value = normalize_hla_serial(
        hla_serial='"\\x54\\x3f\\x6e"',
        serial="ignored",
    )
    assert value == '"\\x54\\x3f\\x6e"'


def test_normalize_from_serial_hex() -> None:
    assert normalize_hla_serial(serial="543f6e") == '"\\x54\\x3f\\x6e"'


def test_normalize_from_raw_bytes() -> None:
    assert normalize_hla_serial(raw_usb_serial=b"\x54\x3f") == '"\\x54\\x3f"'


def test_normalize_printable_ascii() -> None:
    assert normalize_hla_serial(hla_serial="ABC123") == "ABC123"


def test_bytes_to_hla_rejects_empty() -> None:
    with pytest.raises(ValueError):
        bytes_to_hla_serial(b"")
