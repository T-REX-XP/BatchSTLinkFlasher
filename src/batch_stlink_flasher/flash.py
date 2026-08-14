"""CLI: flash one or more discovered ST-Links via OpenOCD.

Usage::

    python -m batch_stlink_flasher.flash --firmware app.elf --target target/stm32f1x.cfg
    python -m batch_stlink_flasher.flash --firmware app.elf --all
    python -m batch_stlink_flasher.flash --firmware app.hex --dry-run
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

from batch_stlink_flasher.flashing.job import FlashJob
from batch_stlink_flasher.flashing.models import AdapterInfo, FlashConfig, JobState
from batch_stlink_flasher.flashing.openocd import (
    build_openocd_command,
    default_bin_base_address,
    format_command_for_shell,
)
from batch_stlink_flasher.flashing.orchestrator import FlashOrchestrator
from batch_stlink_flasher.services.device_service import list_adapters
from batch_stlink_flasher.util.ports import allocate_openocd_ports_batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flash one or more ST-Link targets with OpenOCD"
    )
    parser.add_argument("--firmware", "-f", required=True, type=Path, help="Firmware .elf/.hex/.bin")
    parser.add_argument(
        "--openocd",
        default=None,
        help="OpenOCD executable (default: search PATH)",
    )
    parser.add_argument(
        "--interface",
        default="interface/stlink.cfg",
        help="OpenOCD interface script (default: interface/stlink.cfg)",
    )
    parser.add_argument(
        "--target",
        "-t",
        default="target/stm32f1x.cfg",
        help="OpenOCD target/board script (default: target/stm32f1x.cfg)",
    )
    parser.add_argument(
        "--scripts",
        type=Path,
        default=None,
        help="Optional OpenOCD scripts search path (-s)",
    )
    parser.add_argument(
        "--bin-base",
        default=None,
        help="Flash base for .bin (default 0x08000000)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Soft timeout seconds per job (default 120)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the OpenOCD command(s) and exit without running",
    )
    parser.add_argument(
        "--adapter-index",
        type=int,
        default=None,
        help="1-based adapter index from discovery (default 1 if neither --all nor list)",
    )
    parser.add_argument(
        "--adapters",
        default=None,
        help="Comma-separated 1-based adapter indices (e.g. 1,2,3)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Flash all discovered adapters in parallel",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    openocd = _resolve_openocd(args.openocd)
    if openocd is None and not args.dry_run:
        print("OpenOCD not found. Pass --openocd PATH or add it to PATH.", file=sys.stderr)
        return 2

    firmware = args.firmware
    if not firmware.is_file() and not args.dry_run:
        print(f"Firmware not found: {firmware}", file=sys.stderr)
        return 2

    bin_base = None
    if firmware.suffix.lower() == ".bin" or args.bin_base:
        if args.bin_base:
            bin_base = int(args.bin_base, 0)
        else:
            bin_base = default_bin_base_address()

    config = FlashConfig(
        openocd_path=Path(openocd or "openocd"),
        firmware_path=firmware,
        interface_cfg=args.interface,
        target_cfg=args.target,
        bin_base_address=bin_base,
        scripts_search_path=args.scripts,
        job_timeout_sec=args.timeout,
    )

    all_adapters = list_adapters()
    if not all_adapters:
        print("No ST-Link adapters found.", file=sys.stderr)
        return 1

    try:
        selected = _select_adapters(
            all_adapters,
            all_flag=args.all,
            adapter_index=args.adapter_index,
            adapters_csv=args.adapters,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for adapter in selected:
        _print_adapter(adapter)

    if args.dry_run:
        ports_list = allocate_openocd_ports_batch(len(selected))
        for adapter, ports in zip(selected, ports_list, strict=True):
            hla = (
                adapter.hla_serial.strip()
                if adapter.multi_adapter_ok and adapter.hla_serial
                else None
            )
            if len(selected) > 1 and hla is None:
                print(f"# skip {adapter.serial!r}: no usable HLA serial for parallel run")
                continue
            print(format_command_for_shell(build_openocd_command(config, hla, ports)))
        return 0

    assert openocd is not None

    if len(selected) == 1:
        job = FlashJob(
            selected[0],
            config,
            on_line=lambda line: print(line, flush=True),
        )
        result = job.run()
        print(
            f"\nResult: {result.state.value}  exit={result.exit_code}  "
            f"elapsed={result.elapsed_sec:.1f}s",
            flush=True,
        )
        if result.error_summary:
            print(f"Summary: {result.error_summary}", file=sys.stderr)
        if result.state == JobState.SUCCEEDED:
            return 0
        if result.state == JobState.CANCELLED:
            return 130
        return 1

    orch = FlashOrchestrator(
        selected,
        config,
        on_line=lambda adapter, line: print(f"[{adapter.serial}] {line}", flush=True),
        on_job_done=lambda adapter, result: print(
            f"[{adapter.serial}] done: {result.state.value}"
            + (f" ({result.error_summary})" if result.error_summary else ""),
            flush=True,
        ),
    )
    summary = orch.run()
    print(
        f"\nSummary: {summary.succeeded} succeeded / {summary.failed} failed / "
        f"{summary.cancelled} cancelled (of {summary.total})",
        flush=True,
    )
    if summary.all_succeeded:
        return 0
    if summary.cancelled and summary.succeeded + summary.failed == 0:
        return 130
    return 1


def _select_adapters(
    all_adapters: list[AdapterInfo],
    *,
    all_flag: bool,
    adapter_index: int | None,
    adapters_csv: str | None,
) -> list[AdapterInfo]:
    modes = sum(1 for x in (all_flag, adapter_index is not None, adapters_csv) if x)
    if modes > 1:
        raise ValueError("use only one of --all, --adapter-index, or --adapters")

    if all_flag:
        return list(all_adapters)

    if adapters_csv:
        indices: list[int] = []
        for part in adapters_csv.split(","):
            part = part.strip()
            if not part:
                continue
            indices.append(int(part))
        if not indices:
            raise ValueError("--adapters was empty")
        return [_by_index(all_adapters, i) for i in indices]

    index = 1 if adapter_index is None else adapter_index
    return [_by_index(all_adapters, index)]


def _by_index(adapters: list[AdapterInfo], index: int) -> AdapterInfo:
    if index < 1 or index > len(adapters):
        raise ValueError(f"Adapter index {index} out of range (1..{len(adapters)})")
    return adapters[index - 1]


def _resolve_openocd(explicit: str | None) -> str | None:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        return shutil.which(explicit)
    return shutil.which("openocd") or shutil.which("openocd.exe")


def _print_adapter(adapter: AdapterInfo) -> None:
    print(
        f"Using adapter serial={adapter.serial!r} "
        f"pid=0x{adapter.pid:04x} multi_adapter_ok={adapter.multi_adapter_ok}"
    )
    if adapter.skip_reason:
        print(f"Note: {adapter.skip_reason}")


if __name__ == "__main__":
    raise SystemExit(main())
