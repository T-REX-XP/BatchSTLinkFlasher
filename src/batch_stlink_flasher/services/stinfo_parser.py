"""Parse ``st-info --probe`` stdout into adapter records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FOUND = re.compile(r"^\s*Found\s+(\d+)\s+stlink", re.IGNORECASE)
_KEY_VALUE = re.compile(r"^\s*([A-Za-z0-9_-]+)\s*:\s*(.*)$")


@dataclass
class StinfoProbe:
    """One programmer block from ``st-info --probe``."""

    serial: str = ""
    hla_serial: str = ""
    flash: str = ""
    sram: str = ""
    chipid: str = ""
    descr: str = ""
    version: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def parse_stinfo_probe(stdout: str) -> list[StinfoProbe]:
    """
    Parse ``st-info --probe`` text.

    Supports modern ``hla-serial:`` and older ``openocd:`` fields, including
    line-wrapped escaped serials.
    """
    probes: list[StinfoProbe] = []
    current: StinfoProbe | None = None
    continuation_key: str | None = None

    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continuation_key = None
            continue

        if _FOUND.match(line):
            continuation_key = None
            continue

        match = _KEY_VALUE.match(line)
        if match:
            key = match.group(1).lower().replace("_", "-")
            value = match.group(2).strip()

            if key == "serial":
                current = StinfoProbe(serial=value)
                probes.append(current)
                continuation_key = None
                continue

            if current is None:
                # Orphan fields before first serial — ignore.
                continuation_key = None
                continue

            _assign_field(current, key, value)
            # Multisegment HLA may continue on following lines without a new key.
            if key in {"hla-serial", "openocd"} and value.endswith("\\"):
                continuation_key = key
            else:
                continuation_key = key if key in {"hla-serial", "openocd"} and not value.endswith('"') else None
            continue

        # Continuation line for wrapped hla-serial / openocd values.
        if current is not None and continuation_key in {"hla-serial", "openocd"}:
            piece = line.strip()
            existing = current.hla_serial
            # Drop line-continuation backslash from previous segment.
            if existing.endswith("\\"):
                existing = existing[:-1]
            current.hla_serial = f"{existing}{piece}"
            if piece.endswith('"'):
                continuation_key = None
            continue

    return probes


def _assign_field(probe: StinfoProbe, key: str, value: str) -> None:
    if key in {"hla-serial", "openocd"}:
        probe.hla_serial = value
    elif key == "flash":
        probe.flash = value
    elif key == "sram":
        probe.sram = value
    elif key == "chipid":
        probe.chipid = value
    elif key in {"descr", "description"}:
        probe.descr = value
    elif key == "version":
        probe.version = value
    elif key == "serial":
        probe.serial = value
    else:
        probe.extra[key] = value
