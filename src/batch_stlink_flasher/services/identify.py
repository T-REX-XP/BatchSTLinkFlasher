"""Physically identify an ST-Link by blinking its COM LED."""

from __future__ import annotations

import logging
import time

from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.services.windows_device_control import (
    DeviceIsolationError,
    disable_device,
    enable_device,
)

logger = logging.getLogger(__name__)


def blink_adapter_led(
    adapter: AdapterInfo,
    *,
    pulses: int = 4,
    off_sec: float = 0.35,
    on_sec: float = 0.55,
) -> None:
    """
    Blink the programmer COM LED via USB re-enumeration.

    ST-Link (and most clones) blink the status LED while the USB device
    re-enumerates. There is no portable OpenOCD ``blink led`` command for
    ST-Link HLA, so we briefly disable/enable the PnP node.

    Requires Windows + permission to disable the device (may need elevation).
    Raises ``DeviceIsolationError`` on failure.
    """
    instance_id = (adapter.usb_path or "").strip()
    if not instance_id:
        raise DeviceIsolationError(
            "adapter has no USB instance id; refresh devices and try again"
        )
    if pulses < 1:
        raise ValueError("pulses must be >= 1")

    logger.info(
        "Identify blink: serial=%s port=%s instance=%s pulses=%s",
        adapter.serial,
        adapter.usb_port,
        instance_id,
        pulses,
    )

    # Ensure device ends enabled even if the last pulse fails mid-cycle.
    try:
        for i in range(pulses):
            if not disable_device(instance_id):
                raise DeviceIsolationError(
                    f"could not disable {instance_id} for LED blink "
                    "(try running elevated, or unplug/replug to confirm the LED)"
                )
            time.sleep(off_sec)
            if not enable_device(instance_id):
                raise DeviceIsolationError(
                    f"could not re-enable {instance_id} after blink pulse {i + 1}"
                )
            if i + 1 < pulses:
                time.sleep(on_sec)
    except Exception:
        # Best-effort restore.
        enable_device(instance_id)
        raise
