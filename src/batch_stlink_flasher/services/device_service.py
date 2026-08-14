"""ST-Link discovery via ``st-info``, Windows PnP, then pyusb."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.services.stinfo_parser import StinfoProbe, parse_stinfo_probe
from batch_stlink_flasher.services.windows_pnp import (
    is_usable_usb_serial,
    list_stlink_pnp_devices,
)
from batch_stlink_flasher.util.hla_serial import normalize_hla_serial, strip_hla_quotes
from batch_stlink_flasher.util.win_process import hidden_subprocess_kwargs

logger = logging.getLogger(__name__)

ST_VENDOR_ID = 0x0483

# Common ST-Link product IDs (V2 / V2-1 / V3 and variants).
STLINK_PIDS: frozenset[int] = frozenset(
    {
        0x3744,  # ST-Link (early)
        0x3748,  # ST-Link/V2
        0x374A,  # ST-Link/V2 (NUCLEO-ish)
        0x374B,  # ST-Link/V2-1
        0x374D,
        0x374E,  # STLINK-V3
        0x374F,
        0x3752,
        0x3753,
    }
)

_MISSING_SERIAL_REASON = (
    "Clone / no unique HLA serial. Listed for sequential flash: "
    "siblings are temporarily disabled so OpenOCD targets this probe. "
    "Genuine unique serials enable true parallel flashing."
)


class DeviceDiscoveryError(RuntimeError):
    """Raised when discovery cannot run at all (optional; list APIs usually degrade)."""


def list_adapters(
    *,
    stinfo_path: str | Path | None = None,
    prefer_stinfo: bool = True,
    allow_pyusb_fallback: bool = True,
    allow_windows_pnp: bool = True,
    timeout_sec: float = 15.0,
) -> list[AdapterInfo]:
    """
    Discover connected ST-Link adapters.

    Order:
    1. Windows PnP registry (no console; works with official ST driver)
    2. ``st-info --probe`` when available
    3. pyusb (requires a libusb backend)
    """
    errors: list[str] = []

    if allow_windows_pnp and sys.platform == "win32":
        try:
            adapters = list_adapters_windows_pnp()
            if adapters:
                logger.info("Windows PnP discovered %d adapter(s)", len(adapters))
                return adapters
            errors.append("Windows PnP found no ST-Link devices")
        except Exception as exc:  # noqa: BLE001
            msg = f"Windows PnP failed: {exc}"
            logger.warning(msg)
            errors.append(msg)

    if prefer_stinfo:
        path = _resolve_stinfo(stinfo_path)
        if path is not None:
            try:
                stdout = run_stinfo_probe(path, timeout_sec=timeout_sec)
                adapters = adapters_from_stinfo_stdout(stdout)
                logger.info("st-info discovered %d adapter(s)", len(adapters))
                return adapters
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                msg = f"st-info failed: {exc}"
                logger.warning(msg)
                errors.append(msg)
                if not allow_pyusb_fallback and not allow_windows_pnp:
                    raise DeviceDiscoveryError(str(exc)) from exc
        else:
            errors.append("st-info not found on PATH")
            if not allow_pyusb_fallback and not allow_windows_pnp:
                raise DeviceDiscoveryError("st-info not found on PATH")

    if allow_pyusb_fallback:
        adapters = list_adapters_pyusb()
        if adapters:
            logger.info("pyusb discovered %d adapter(s)", len(adapters))
            return adapters
        errors.append("pyusb found no adapters (often: No backend available / missing libusb)")

    for err in errors:
        logger.warning("discovery: %s", err)
    return []


def run_stinfo_probe(stinfo_path: str | Path, *, timeout_sec: float = 15.0) -> str:
    """Run ``st-info --probe`` and return stdout."""
    cmd = [str(stinfo_path), "--probe"]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
        **hidden_subprocess_kwargs(),
    )
    stdout = completed.stdout or ""
    if completed.returncode != 0 and not stdout.strip():
        err = (completed.stderr or "").strip() or f"exit {completed.returncode}"
        raise subprocess.CalledProcessError(completed.returncode, cmd, output=stdout, stderr=err)
    return stdout


def adapters_from_stinfo_stdout(stdout: str) -> list[AdapterInfo]:
    """Convert parsed ``st-info --probe`` text into ``AdapterInfo`` rows."""
    return [
        _probe_to_adapter(probe)
        for probe in parse_stinfo_probe(stdout)
        if probe.serial or probe.hla_serial
    ]


def list_adapters_windows_pnp() -> list[AdapterInfo]:
    """Enumerate ST-Links via Windows PnP (works with ST's driver)."""
    adapters: list[AdapterInfo] = []
    for dev in list_stlink_pnp_devices():
        if STLINK_PIDS and dev.pid not in STLINK_PIDS:
            logger.debug("skipping ST VID PnP device with non-ST-Link PID 0x%04x", dev.pid)
            continue

        if is_usable_usb_serial(dev.usb_serial):
            try:
                # Prefer treating instance serial as USB string bytes / text.
                hla = normalize_hla_serial(raw_usb_serial=dev.usb_serial)
            except ValueError:
                try:
                    hla = normalize_hla_serial(serial=dev.usb_serial)
                except ValueError as exc:
                    logger.warning("PnP serial normalize failed for %s: %s", dev.instance_id, exc)
                    hla = ""
            multi_ok = bool(hla)
            reason = None if multi_ok else _MISSING_SERIAL_REASON
            display_serial = (
                dev.usb_serial
                if re.fullmatch(r"[0-9A-Fa-f]+", dev.usb_serial)
                else _display_serial(dev.usb_serial)
            )
        else:
            hla = ""
            multi_ok = False
            reason = _MISSING_SERIAL_REASON
            display_serial = dev.usb_serial or "(none)"

        adapters.append(
            AdapterInfo(
                serial=display_serial,
                hla_serial=hla,
                vid=dev.vid,
                pid=dev.pid,
                product=dev.name or "ST-Link",
                manufacturer=dev.manufacturer or "STMicroelectronics",
                usb_path=dev.instance_id,
                multi_adapter_ok=multi_ok,
                skip_reason=reason,
            )
        )
    return adapters


def list_adapters_pyusb() -> list[AdapterInfo]:
    """Enumerate ST-Links via pyusb. Returns [] if backend/devices unavailable."""
    try:
        import usb.core  # type: ignore[import-untyped]
        import usb.util  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("pyusb is not installed; cannot fall back to USB enumeration")
        return []

    adapters: list[AdapterInfo] = []
    try:
        devices = list(usb.core.find(find_all=True, idVendor=ST_VENDOR_ID) or [])
    except Exception as exc:  # noqa: BLE001 — backend/driver errors vary by OS
        logger.warning("pyusb enumeration failed: %s", exc)
        return []

    for dev in devices:
        pid = int(dev.idProduct)
        if pid not in STLINK_PIDS:
            logger.debug("skipping ST VID device with non-ST-Link PID 0x%04x", pid)
            continue

        serial_str = _read_usb_serial(dev, usb.util)
        if not serial_str:
            logger.debug("skipping device pid=0x%04x with no iSerial", pid)
            continue

        usable = is_usable_usb_serial(serial_str)
        hla = ""
        reason = None
        multi_ok = False
        if usable:
            try:
                hla = normalize_hla_serial(raw_usb_serial=serial_str)
                multi_ok = True
            except ValueError as exc:
                logger.warning("could not normalize serial for pid=0x%04x: %s", pid, exc)
                reason = str(exc)
        else:
            reason = _MISSING_SERIAL_REASON

        product = _usb_string(dev, getattr(dev, "iProduct", 0), usb.util) or "ST-Link"
        manufacturer = _usb_string(dev, getattr(dev, "iManufacturer", 0), usb.util) or ""
        usb_path = f"{getattr(dev, 'bus', '?')}:{getattr(dev, 'address', '?')}"

        adapters.append(
            AdapterInfo(
                serial=_display_serial(serial_str) if serial_str else "(none)",
                hla_serial=hla,
                vid=ST_VENDOR_ID,
                pid=pid,
                product=product,
                manufacturer=manufacturer,
                usb_path=usb_path,
                multi_adapter_ok=multi_ok,
                skip_reason=reason,
            )
        )

    return adapters


def _probe_to_adapter(probe: StinfoProbe) -> AdapterInfo:
    hla = normalize_hla_serial(
        hla_serial=probe.hla_serial or None,
        serial=probe.serial or None,
    )
    product = probe.descr or probe.version or "ST-Link"
    return AdapterInfo(
        serial=probe.serial or _display_from_hla(hla),
        hla_serial=hla,
        vid=ST_VENDOR_ID,
        pid=0,
        product=product,
        manufacturer="STMicroelectronics",
        usb_path=None,
        multi_adapter_ok=True,
        skip_reason=None,
    )


def _resolve_stinfo(stinfo_path: str | Path | None) -> str | None:
    if stinfo_path is not None:
        explicit = Path(stinfo_path)
        if explicit.exists():
            return str(explicit)
        return shutil.which(str(stinfo_path))
    return shutil.which("st-info")


def _read_usb_serial(dev: object, usb_util: object) -> str | None:
    try:
        return usb_util.get_string(dev, dev.iSerialNumber)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return None


def _usb_string(dev: object, index: int, usb_util: object) -> str:
    if not index:
        return ""
    try:
        return str(usb_util.get_string(dev, index) or "")
    except Exception:  # noqa: BLE001
        return ""


def _display_serial(serial_str: str) -> str:
    raw = serial_str.encode("latin-1", errors="surrogateescape")
    return raw.hex()


def _display_from_hla(hla: str) -> str:
    inner = strip_hla_quotes(hla)
    pairs = re.findall(r"\\x([0-9A-Fa-f]{2})", inner)
    if pairs:
        return "".join(pairs).lower()
    return inner
