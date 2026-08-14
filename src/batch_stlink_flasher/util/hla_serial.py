"""Normalize ST-Link serials into OpenOCD ``hla_serial`` argument form."""

from __future__ import annotations

import re

_HEX_PAIR = re.compile(r"^[0-9A-Fa-f]{2}(?:[0-9A-Fa-f]{2})*$")
_ESCAPED_BYTE = re.compile(r"\\x[0-9A-Fa-f]{2}")


def strip_hla_quotes(value: str) -> str:
    """Remove surrounding double quotes from an HLA / openocd serial string."""
    text = value.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def bytes_to_hla_serial(data: bytes, *, strip_trailing_nulls: bool = True) -> str:
    """
    Convert raw USB serial bytes to an OpenOCD ``hla_serial`` value.

    Returns a quoted ``\"\\xNN...\"`` string ready to append after ``hla_serial ``.
    """
    payload = data
    if strip_trailing_nulls:
        payload = payload.rstrip(b"\x00")
    if not payload:
        raise ValueError("serial bytes are empty")
    escaped = "".join(f"\\x{b:02x}" for b in payload)
    return f'"{escaped}"'


def hex_serial_to_hla(hex_serial: str, *, strip_trailing_nulls: bool = True) -> str:
    """
    Convert st-info ``serial:`` hex text (e.g. ``30303341…``) to OpenOCD HLA form.
    """
    cleaned = "".join(hex_serial.split())
    if not cleaned:
        raise ValueError("hex serial is empty")
    if not _HEX_PAIR.fullmatch(cleaned):
        raise ValueError(f"serial is not even-length hex: {hex_serial!r}")
    return bytes_to_hla_serial(bytes.fromhex(cleaned), strip_trailing_nulls=strip_trailing_nulls)


def normalize_hla_serial(
    *,
    hla_serial: str | None = None,
    serial: str | None = None,
    raw_usb_serial: bytes | str | None = None,
) -> str:
    """
    Produce a value suitable for OpenOCD ``-c 'hla_serial …'``.

    Preference order:
    1. ``hla_serial`` / ``openocd`` field from st-info (already escaped)
    2. hex ``serial`` field from st-info
    3. raw USB iSerial string/bytes (pyusb)
    """
    if hla_serial and hla_serial.strip():
        return _normalize_escaped_or_literal(hla_serial)

    if serial and serial.strip():
        cleaned = "".join(serial.split())
        if _HEX_PAIR.fullmatch(cleaned):
            return hex_serial_to_hla(cleaned)
        return _normalize_escaped_or_literal(serial)

    if raw_usb_serial is not None:
        if isinstance(raw_usb_serial, str):
            raw_usb_serial = raw_usb_serial.encode("latin-1", errors="surrogateescape")
        return bytes_to_hla_serial(raw_usb_serial)

    raise ValueError("no serial material provided for HLA normalization")


def _normalize_escaped_or_literal(value: str) -> str:
    """Ensure escaped HLA strings are quoted; leave printable ASCII as-is (quoted if needed)."""
    compact = "".join(value.split())  # join wrapped hla-serial lines
    inner = strip_hla_quotes(compact)

    if _ESCAPED_BYTE.search(inner):
        # Keep only \\xNN sequences if present; tolerate already-escaped text.
        if not inner.startswith("\\x") and '"' not in inner:
            # Unusual form — quote as literal for OpenOCD.
            return f'"{inner}"'
        return f'"{inner}"'

    # Printable serial without escapes (rare for ST-Link V2 clones).
    if all(32 <= ord(ch) < 127 and ch not in {'"', "\\"} for ch in inner):
        return inner

    return bytes_to_hla_serial(inner.encode("latin-1", errors="surrogateescape"))
