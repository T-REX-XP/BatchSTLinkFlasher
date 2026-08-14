"""Enable/disable Windows PnP device nodes (used to isolate clone ST-Links)."""

from __future__ import annotations

import ctypes
import logging
import sys
from contextlib import contextmanager
from ctypes import wintypes
from typing import Iterator

logger = logging.getLogger(__name__)

_CM_LOCATE_DEVNODE_NORMAL = 0
_CR_SUCCESS = 0
# CONFIGRET codes (cfgmgr32.h)
_CR_ACCESS_DENIED = 51  # 0x33
# Allow disable even if UI would normally prompt.
_CM_DISABLE_UI_NOT_OK = 0x00000001

_last_cm_status: int | None = None


class DeviceIsolationError(RuntimeError):
    """Raised when sibling ST-Links cannot be disabled for an unbound flash."""


class DeviceAccessDeniedError(DeviceIsolationError):
    """PnP disable/enable denied — usually needs Administrator."""


def last_cm_status() -> int | None:
    """Most recent CONFIGRET from a CM_* call in this module (tests / diagnose)."""
    return _last_cm_status


def _set_status(status: int) -> None:
    global _last_cm_status
    _last_cm_status = int(status)


def _cfgmgr32() -> ctypes.WinDLL:
    dll = ctypes.WinDLL("cfgmgr32", use_last_error=True)
    try:
        dll.CM_Locate_DevNodeW.argtypes = [
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPCWSTR,
            wintypes.ULONG,
        ]
        dll.CM_Locate_DevNodeW.restype = wintypes.DWORD
        dll.CM_Disable_DevNode.argtypes = [wintypes.DWORD, wintypes.ULONG]
        dll.CM_Disable_DevNode.restype = wintypes.DWORD
        dll.CM_Enable_DevNode.argtypes = [wintypes.DWORD, wintypes.ULONG]
        dll.CM_Enable_DevNode.restype = wintypes.DWORD
    except AttributeError:
        pass
    return dll


def locate_dev_inst(instance_id: str) -> int | None:
    """Return Config Manager DEVINST for ``instance_id``, or None."""
    if sys.platform != "win32":
        return None
    try:
        cfgmgr32 = _cfgmgr32()
        dev_inst = wintypes.DWORD()
        status = cfgmgr32.CM_Locate_DevNodeW(
            ctypes.byref(dev_inst),
            instance_id,
            _CM_LOCATE_DEVNODE_NORMAL,
        )
        _set_status(status)
        if status != _CR_SUCCESS:
            return None
        return int(dev_inst.value)
    except (AttributeError, OSError, ValueError) as exc:
        logger.debug("CM_Locate_DevNode failed for %s: %s", instance_id, exc)
        return None


def disable_device(instance_id: str) -> bool:
    """Disable a PnP device node. Returns True on success."""
    if sys.platform != "win32":
        return False
    dev_inst = locate_dev_inst(instance_id)
    if dev_inst is None:
        return False
    try:
        cfgmgr32 = _cfgmgr32()
        status = int(cfgmgr32.CM_Disable_DevNode(dev_inst, _CM_DISABLE_UI_NOT_OK))
        _set_status(status)
        ok = status == _CR_SUCCESS
        if not ok:
            logger.warning("CM_Disable_DevNode(%s) -> %s", instance_id, status)
        return ok
    except (AttributeError, OSError, ValueError) as exc:
        logger.warning("disable_device(%s) failed: %s", instance_id, exc)
        return False


def enable_device(instance_id: str) -> bool:
    """Re-enable a PnP device node. Returns True on success."""
    if sys.platform != "win32":
        return False
    # After disable, NORMAL locate can fail; try phantom as well.
    dev_inst = locate_dev_inst(instance_id)
    if dev_inst is None:
        try:
            cfgmgr32 = _cfgmgr32()
            node = wintypes.DWORD()
            # CM_LOCATE_DEVNODE_PHANTOM = 0x00000001
            status = cfgmgr32.CM_Locate_DevNodeW(ctypes.byref(node), instance_id, 1)
            _set_status(status)
            if status != _CR_SUCCESS:
                return False
            dev_inst = int(node.value)
        except (AttributeError, OSError, ValueError):
            return False
    try:
        cfgmgr32 = _cfgmgr32()
        status = int(cfgmgr32.CM_Enable_DevNode(dev_inst, 0))
        _set_status(status)
        ok = status == _CR_SUCCESS
        if not ok:
            logger.warning("CM_Enable_DevNode(%s) -> %s", instance_id, status)
        return ok
    except (AttributeError, OSError, ValueError) as exc:
        logger.warning("enable_device(%s) failed: %s", instance_id, exc)
        return False


def is_access_denied_status(status: int | None = None) -> bool:
    """True when the last (or given) CONFIGRET is CR_ACCESS_DENIED."""
    code = _last_cm_status if status is None else status
    return code == _CR_ACCESS_DENIED


def access_denied_hint(instance_id: str) -> str:
    return (
        f"Windows denied disabling {instance_id} (need Administrator). "
        "Approve the UAC prompt for Identify LED, or restart the app as Administrator."
    )


@contextmanager
def isolated_usb_device(
    target_instance_id: str,
    sibling_instance_ids: list[str],
) -> Iterator[None]:
    """
    Temporarily disable sibling USB devices so OpenOCD sees only ``target``.

    Used for clone ST-Links that lack a unique HLA serial: with siblings
    disabled, a single OpenOCD process (no ``hla_serial``) attaches to the
    remaining probe. Always re-enables siblings, even on failure.

    Raises ``DeviceIsolationError`` if any sibling cannot be disabled.
    """
    target = (target_instance_id or "").strip()
    if not target:
        raise DeviceIsolationError("target adapter has no USB instance id")

    siblings = [
        sid
        for sid in sibling_instance_ids
        if sid and sid.strip().upper() != target.upper()
    ]
    if not siblings:
        yield
        return

    if sys.platform != "win32":
        raise DeviceIsolationError(
            "clone multi-adapter isolation requires Windows device control"
        )

    disabled: list[str] = []
    try:
        for sid in siblings:
            if disable_device(sid):
                disabled.append(sid)
            else:
                msg = (
                    access_denied_hint(sid)
                    if is_access_denied_status()
                    else (
                        f"could not disable sibling ST-Link {sid}. "
                        "Run the app elevated, or unplug other probes, "
                        "or use ST-Links with unique serials for parallel flash."
                    )
                )
                raise DeviceIsolationError(msg)
        yield
    finally:
        for sid in reversed(disabled):
            if not enable_device(sid):
                logger.error("failed to re-enable ST-Link %s after isolation", sid)
