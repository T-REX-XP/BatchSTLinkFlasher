"""Windows Plug and Play USB enumeration for ST-Links (no libusb required)."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# USB\VID_0483&PID_3748\<serial>
_INSTANCE_RE = re.compile(
    r"^USB\\VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})\\(.+)$",
    re.IGNORECASE,
)

_UNUSABLE_SERIALS = frozenset({"", "%", "000000000000", "0"})


@dataclass(frozen=True)
class WindowsUsbDevice:
    name: str
    manufacturer: str
    instance_id: str
    vid: int
    pid: int
    usb_serial: str


def list_stlink_pnp_devices() -> list[WindowsUsbDevice]:
    """
    List present ST USB devices via Win32_PnPEntity.

    Works with the official STMicroelectronics WinUSB/ST driver (no pyusb backend).
    """
    if sys.platform != "win32":
        return []

    raw = _query_pnp_json()
    if not raw:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("failed to parse Windows PnP JSON: %s", exc)
        return []

    if isinstance(payload, dict):
        rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        return []

    devices: list[WindowsUsbDevice] = []
    for row in rows:
        instance_id = str(row.get("DeviceID") or row.get("InstanceId") or "")
        parsed = parse_usb_instance_id(instance_id)
        if parsed is None:
            continue
        vid, pid, serial = parsed
        devices.append(
            WindowsUsbDevice(
                name=str(row.get("Name") or row.get("FriendlyName") or "ST-Link"),
                manufacturer=str(row.get("Manufacturer") or ""),
                instance_id=instance_id,
                vid=vid,
                pid=pid,
                usb_serial=serial,
            )
        )
    return devices


def parse_usb_instance_id(instance_id: str) -> tuple[int, int, str] | None:
    """Return ``(vid, pid, serial)`` from a USB device instance ID, if it matches."""
    match = _INSTANCE_RE.match(instance_id.strip())
    if not match:
        return None
    vid = int(match.group(1), 16)
    pid = int(match.group(2), 16)
    serial = match.group(3)
    return vid, pid, serial


def is_usable_usb_serial(serial: str) -> bool:
    """False for empty / placeholder serials common on clone ST-Link V2 sticks."""
    text = (serial or "").strip()
    if text in _UNUSABLE_SERIALS:
        return False
    # Single punctuation / wildcard placeholders
    if len(text) <= 1:
        return False
    return True


def _query_pnp_json() -> str:
    """Run PowerShell to dump present ST VID USB devices as JSON."""
    script = (
        "$ErrorActionPreference = 'Stop'; "
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.DeviceID -like 'USB\\VID_0483*' } | "
        "Select-Object Name, Manufacturer, DeviceID | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Windows PnP query failed: %s", exc)
        return ""

    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        logger.warning("Windows PnP query exit %s: %s", completed.returncode, err)
        return ""

    return (completed.stdout or "").strip()
