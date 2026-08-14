"""Physically identify an ST-Link by blinking its COM LED."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.services.windows_device_control import (
    DeviceIsolationError,
    access_denied_hint,
    disable_device,
    enable_device,
    is_access_denied_status,
)

logger = logging.getLogger(__name__)

_ENV_SKIP_ELEVATE = "BATCH_STLINK_IDENTIFY_NO_ELEVATE"


def blink_adapter_led(
    adapter: AdapterInfo,
    *,
    pulses: int = 4,
    off_sec: float = 0.4,
    on_sec: float = 0.6,
    allow_elevate: bool = True,
) -> None:
    """
    Blink the programmer COM LED via USB re-enumeration.

    ST-Link (and most clones) blink the status LED while the USB device
    re-enumerates. There is no portable OpenOCD ``blink led`` command for
    ST-Link HLA, so we briefly disable/enable the PnP node.

    On access denied, optionally re-runs the blink in an elevated helper
    (UAC prompt). Set ``allow_elevate=False`` in that helper to avoid loops.
    """
    instance_id = (adapter.usb_path or "").strip()
    if not instance_id:
        raise DeviceIsolationError(
            "adapter has no USB instance id; refresh devices and try again"
        )
    if pulses < 1:
        raise ValueError("pulses must be >= 1")

    logger.info(
        "Identify blink: serial=%s port=%s instance=%s pulses=%s elevate=%s",
        adapter.serial,
        adapter.usb_port,
        instance_id,
        pulses,
        allow_elevate,
    )

    try:
        _blink_pnp(instance_id, pulses=pulses, off_sec=off_sec, on_sec=on_sec)
        return
    except DeviceIsolationError as exc:
        if not allow_elevate or not is_access_denied_status():
            raise
        if os.environ.get(_ENV_SKIP_ELEVATE, "").strip() in {"1", "true", "yes"}:
            raise DeviceIsolationError(access_denied_hint(instance_id)) from exc
        logger.info("Identify PnP denied; requesting elevation")
        _blink_elevated(instance_id, pulses=pulses, off_sec=off_sec, on_sec=on_sec)


def _blink_pnp(
    instance_id: str,
    *,
    pulses: int,
    off_sec: float,
    on_sec: float,
) -> None:
    try:
        for i in range(pulses):
            if not disable_device(instance_id):
                if is_access_denied_status():
                    raise DeviceIsolationError(access_denied_hint(instance_id))
                raise DeviceIsolationError(
                    f"could not disable {instance_id} for LED blink "
                    "(device busy, or unsupported by the driver)"
                )
            time.sleep(off_sec)
            if not enable_device(instance_id):
                raise DeviceIsolationError(
                    f"could not re-enable {instance_id} after blink pulse {i + 1}"
                )
            if i + 1 < pulses:
                time.sleep(on_sec)
    except Exception:
        enable_device(instance_id)
        raise


def _blink_elevated(
    instance_id: str,
    *,
    pulses: int,
    off_sec: float,
    on_sec: float,
) -> None:
    from batch_stlink_flasher.util.win_elevate import is_user_an_admin, run_elevated

    if is_user_an_admin():
        # Already elevated but still denied — nothing more we can do.
        raise DeviceIsolationError(access_denied_hint(instance_id))

    payload = {
        "instance_id": instance_id,
        "pulses": pulses,
        "off_sec": off_sec,
        "on_sec": on_sec,
    }
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="batch_stlink_identify_",
        delete=False,
        encoding="utf-8",
    )
    try:
        json.dump(payload, tmp)
        tmp.close()
        job = Path(tmp.name)
        exe, params = _elevated_launch_args(job)
        logger.info("Elevated identify: %s %s", exe, params)
        try:
            code = run_elevated(exe, params)
        except OSError as exc:
            # 1223 = ERROR_CANCELLED (UAC declined)
            if getattr(exc, "winerror", None) == 1223 or exc.errno == 1223:
                raise DeviceIsolationError(
                    "Identify LED canceled — UAC elevation was declined. "
                    "Approve the prompt, or run the app as Administrator."
                ) from exc
            raise DeviceIsolationError(
                f"could not elevate Identify LED helper: {exc}"
            ) from exc
        if code != 0:
            raise DeviceIsolationError(
                f"elevated Identify LED failed (exit {code}). "
                "Try Run as Administrator, or use the USB port column."
            )
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except OSError:
            pass


def _elevated_launch_args(job_path: Path) -> tuple[str, str]:
    """Return (exe, parameters) for an elevated identify-blink child."""
    job = str(job_path)
    if getattr(sys, "frozen", False):
        return sys.executable, f'--identify-blink "{job}"'
    # Dev: elevate the same Python with -m
    return sys.executable, f'-m batch_stlink_flasher --identify-blink "{job}"'


def run_identify_blink_job(job_path: str | Path) -> int:
    """
    Elevated / headless entry: read job JSON and blink without further elevation.

    Returns process exit code (0 = ok).
    """
    path = Path(job_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("identify job read failed: %s", exc)
        return 2

    instance_id = str(data.get("instance_id") or "").strip()
    if not instance_id:
        return 2
    pulses = max(1, int(data.get("pulses") or 4))
    off_sec = float(data.get("off_sec") or 0.4)
    on_sec = float(data.get("on_sec") or 0.6)

    adapter = AdapterInfo(
        serial="identify",
        hla_serial="",
        vid=0,
        pid=0,
        usb_path=instance_id,
        multi_adapter_ok=False,
    )
    try:
        blink_adapter_led(
            adapter,
            pulses=pulses,
            off_sec=off_sec,
            on_sec=on_sec,
            allow_elevate=False,
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error("identify blink job failed: %s", exc)
        return 1
