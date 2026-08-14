"""CLI: list connected ST-Link adapters.

Usage::

    python -m batch_stlink_flasher.discover
    python -m batch_stlink_flasher.discover --st-info path/to/st-info.exe
    python -m batch_stlink_flasher.discover --pyusb-only
"""

from __future__ import annotations

import argparse
import logging
import sys

from batch_stlink_flasher.services.device_service import list_adapters


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List connected ST-Link adapters")
    parser.add_argument(
        "--st-info",
        dest="stinfo_path",
        default=None,
        help="Path or name of st-info executable (default: search PATH)",
    )
    parser.add_argument(
        "--pyusb-only",
        action="store_true",
        help="Skip st-info / Windows PnP and enumerate via pyusb only",
    )
    parser.add_argument(
        "--no-pyusb-fallback",
        action="store_true",
        help="Do not fall back to pyusb",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show discovery warnings on stderr",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    adapters = list_adapters(
        stinfo_path=args.stinfo_path,
        prefer_stinfo=not args.pyusb_only,
        allow_windows_pnp=not args.pyusb_only,
        allow_pyusb_fallback=not args.no_pyusb_fallback,
    )

    if not adapters:
        print("No ST-Link adapters found.")
        print(
            "Hints: install stlink tools (st-info), or on Windows rely on PnP "
            "(official ST driver is enough). pyusb needs a libusb backend and "
            "usually does not work with the stock ST driver.",
            file=sys.stderr,
        )
        return 1

    print(f"Found {len(adapters)} adapter(s):")
    for i, adapter in enumerate(adapters, start=1):
        print(f"  [{i}] serial={adapter.serial}")
        print(f"      hla_serial={adapter.hla_serial or '(none)'}")
        print(f"      vid=0x{adapter.vid:04x} pid=0x{adapter.pid:04x}")
        print(f"      product={adapter.product!r} manufacturer={adapter.manufacturer!r}")
        if adapter.usb_port is not None:
            hub = f" hub={adapter.usb_hub}" if adapter.usb_hub is not None else ""
            print(f"      usb_port={adapter.usb_port}{hub}")
        if adapter.usb_path:
            print(f"      usb_path={adapter.usb_path}")
        print(f"      multi_adapter_ok={adapter.multi_adapter_ok}")
        if adapter.skip_reason:
            print(f"      note={adapter.skip_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
