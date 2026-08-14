"""Windows Plug and Play USB enumeration for ST-Links (no libusb / no PowerShell)."""

from __future__ import annotations

import ctypes
import logging
import re
import sys
import winreg
from ctypes import wintypes
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# USB\VID_0483&PID_3748\<serial>
_INSTANCE_RE = re.compile(
    r"^USB\\VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})\\(.+)$",
    re.IGNORECASE,
)
# Windows-generated composite/hub instance suffixes — not OpenOCD HLA serials.
_COMPOSITE_SERIAL_RE = re.compile(r"^\d+&[0-9A-Fa-f]+&\d+&\d+$", re.IGNORECASE)

_UNUSABLE_SERIALS = frozenset({"", "%", "000000000000", "0"})
_USB_ENUM_ROOT = r"SYSTEM\CurrentControlSet\Enum\USB"
_ST_VID_PREFIX = "VID_0483"

_CM_LOCATE_DEVNODE_NORMAL = 0
_CR_SUCCESS = 0
_DN_STARTED = 0x00000008


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
    List present ST USB devices via the Windows device registry + Config Manager.

    Works with the official STMicroelectronics WinUSB/ST driver (no libusb backend).
    Does **not** spawn PowerShell / console processes (avoids black console flash).
    """
    if sys.platform != "win32":
        return []

    try:
        rows = _enumerate_stlink_registry()
    except OSError as exc:
        logger.warning("Windows PnP registry query failed: %s", exc)
        return []

    devices: list[WindowsUsbDevice] = []
    seen_serials: set[str] = set()
    for row in rows:
        instance_id = str(row.get("DeviceID") or "")
        parsed = parse_usb_instance_id(instance_id)
        if parsed is None:
            continue
        vid, pid, serial = parsed
        if _COMPOSITE_SERIAL_RE.match(serial):
            # Skip hub/composite interface instance IDs (not usable as HLA serial).
            continue
        key = serial.upper()
        if key in seen_serials:
            continue
        seen_serials.add(key)
        devices.append(
            WindowsUsbDevice(
                name=str(row.get("Name") or "ST-Link"),
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


def _enumerate_stlink_registry() -> list[dict[str, str]]:
    """
    Walk HKLM\\SYSTEM\\CurrentControlSet\\Enum\\USB for present VID_0483 devices.

    Presence is determined with ``CM_Locate_DevNode`` / ``CM_Get_DevNode_Status``
    (``DN_STARTED``). The old ``Control`` registry subkey heuristic is unreliable
    with the official ST driver on Windows 10/11.
    """
    rows: list[dict[str, str]] = []
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _USB_ENUM_ROOT) as usb_root:
        for hardware_id in _enum_subkeys(usb_root):
            if not hardware_id.upper().startswith(_ST_VID_PREFIX):
                continue
            hw_path = f"{_USB_ENUM_ROOT}\\{hardware_id}"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, hw_path) as hw_key:
                    for instance in _enum_subkeys(hw_key):
                        inst_path = f"{hw_path}\\{instance}"
                        device_id = f"USB\\{hardware_id}\\{instance}"
                        if not _device_present(device_id):
                            continue
                        props = _read_device_props(inst_path)
                        rows.append(
                            {
                                "Name": props.get("FriendlyName")
                                or props.get("DeviceDesc")
                                or "ST-Link",
                                "Manufacturer": props.get("Mfg") or "",
                                "DeviceID": device_id,
                            }
                        )
            except OSError as exc:
                logger.debug("skip USB node %s: %s", hardware_id, exc)
                continue
    return rows


def _enum_subkeys(key) -> list[str]:
    names: list[str] = []
    index = 0
    while True:
        try:
            names.append(winreg.EnumKey(key, index))
        except OSError:
            break
        index += 1
    return names


def _device_present(instance_id: str) -> bool:
    """
    True when Config Manager reports the device node as started.

    ``instance_id`` is the PnP instance id, e.g. ``USB\\VID_0483&PID_3748\\%``.
    """
    try:
        cfgmgr32 = ctypes.WinDLL("cfgmgr32", use_last_error=True)
        dev_inst = wintypes.DWORD()
        locate = cfgmgr32.CM_Locate_DevNodeW(
            ctypes.byref(dev_inst),
            instance_id,
            _CM_LOCATE_DEVNODE_NORMAL,
        )
        if locate != _CR_SUCCESS:
            return False
        status_flags = wintypes.DWORD()
        problem = wintypes.ULONG()
        status = cfgmgr32.CM_Get_DevNode_Status(
            ctypes.byref(status_flags),
            ctypes.byref(problem),
            dev_inst,
            0,
        )
        if status != _CR_SUCCESS:
            return False
        return bool(status_flags.value & _DN_STARTED)
    except (AttributeError, OSError, ValueError) as exc:
        logger.debug("CM presence check failed for %s: %s", instance_id, exc)
        # Last-resort: Control subkey (works on some driver stacks).
        if not instance_id.upper().startswith("USB\\"):
            return False
        rel = instance_id.split("\\", 1)[1]
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{_USB_ENUM_ROOT}\\{rel}\\Control"):
                return True
        except OSError:
            return False


def _read_device_props(instance_path: str) -> dict[str, str]:
    props: dict[str, str] = {}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, instance_path) as key:
            for name in ("FriendlyName", "DeviceDesc", "Mfg"):
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                except OSError:
                    continue
                text = _clean_reg_string(str(value))
                if text:
                    props[name] = text
    except OSError:
        return props
    return props


def _clean_reg_string(value: str) -> str:
    # DeviceDesc / Mfg often look like "@oemXX.inf,%desc%;STM32 STLink"
    if ";" in value:
        value = value.rsplit(";", 1)[-1]
    return value.strip()
