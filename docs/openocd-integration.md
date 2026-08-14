# OpenOCD integration

## Prerequisites

- OpenOCD installed and runnable (`openocd -v`).
- Scripts directory available (often shipped with the install). Use `-s <scripts_dir>` if needed.
- Optional but recommended: [stlink tools](https://github.com/stlink-org/stlink) (`st-info --probe`) for reliable serial listing.

## Multi-adapter rules

When several ST-Links are connected:

1. **Identify** each by USB/HLA serial (`st-info --probe` prints `serial` and often an OpenOCD-oriented form).
2. **Bind** each OpenOCD instance with `-c "hla_serial <value>"` (or `adapter serial` on newer OpenOCD + `interface/stlink.cfg`).
3. **Isolate ports** per instance so GDB/telnet/tcl do not collide.

Example port scheme for job index `i` (0-based), base `3333`:

| Port role | Value |
|-----------|--------|
| gdb_port | `3333 + 3*i` |
| telnet_port | `3334 + 3*i` |
| tcl_port | `3335 + 3*i` |

Or allocate ephemeral free ports at runtime (preferred).

## Example flash command (one device)

```text
openocd
  -f interface/stlink.cfg
  -f target/stm32f1x.cfg
  -c "hla_serial SERIAL_HERE"
  -c "gdb_port 3333"
  -c "telnet_port 4444"
  -c "tcl_port 6666"
  -c "program path/to/firmware.elf verify reset exit"
```

For `.bin`:

```text
-c "program path/to/firmware.bin 0x08000000 verify reset exit"
```

Adjust `interface` / `target` (or `board/...`) to the product under test. Wrong target is a common cause of “Failed” while siblings succeed.

## Obtaining serials

### Preferred: st-info

```text
st-info --probe
```

Parse each probe block for `serial:` and `hla-serial:` (older tools: `openocd:`).  
App entry: `python -m batch_stlink_flasher.discover`

### HLA normalization (app)

Use `batch_stlink_flasher.util.hla_serial.normalize_hla_serial`:

| Source | Handling |
|--------|----------|
| `hla-serial` / `openocd` | Keep `\xNN` escapes; ensure quoted (`"\x54\x3f…"`) |
| `serial` hex text | Pairwise hex → bytes → quoted `\xNN` (strip trailing `0x00`) |
| pyusb iSerial | Encode latin-1 bytes → quoted `\xNN` |

Pass the normalized string to OpenOCD as one `-c` argument:

```text
-c hla_serial "\x54\x3f\x6e\x06\x72\x3f\x49\x55\x07\x37\x22\x67"
```

(`build_openocd_command` inserts `hla_serial ` + normalized value.)

### Fallback: wrong serial + debug log

```text
openocd -d3 -f interface/stlink.cfg -f target/stm32f1x.cfg -c "hla_serial wrong_serial"
```

Search log for `Device serial number '…' doesn't match`.

### Fallback: Windows PnP (recommended on Windows)

The app reads present ST devices from the USB device registry
(`HKLM\SYSTEM\CurrentControlSet\Enum\USB\VID_0483...`) — **no PowerShell /
console process**. Instance IDs look like:
`USB\VID_0483&PID_3748\<serial>` using the **official ST driver**.
No libusb / Zadig change is required for discovery.

Clone ST-Link V2 devices often expose a placeholder serial (`%`). Those probes
are still listed (`multi_adapter_ok=false`); OpenOCD can flash them when they
are the **only** adapter (`FlashJob` / `build_openocd_command` omit `hla_serial`).
Genuine unique serials are required for parallel multi-adapter runs.

### Fallback: pyusb

Filter `idVendor == 0x0483` and known ST-Link PIDs (see `STLINK_PIDS` in `device_service.py`).
Requires a **libusb** backend. With the stock STMicroelectronics driver this
usually fails with `No backend available` — prefer Windows PnP or install
`st-info` instead of forcing Zadig unless you know you need WinUSB.

## Process lifecycle (app)

1. Build argv; start process with pipes for stdout/stderr.
2. Append every line to the device log (prefix timestamp optional).
3. On exit code `0` → Succeeded; else Failed (capture last lines containing `Error`, `fail`, `Couldn't`).
4. On cancel/timeout → terminate process tree; state Cancelled or Failed(timeout).
5. Never reuse ports until the previous process has exited.

## Verification

v1: use OpenOCD `program … verify …`. Do not implement separate read-back unless requirements change.

## Troubleshooting cheat sheet

| Symptom | Likely cause |
|---------|----------------|
| `libusb_open() failed` | Driver/Zadig, device in use by another tool |
| Wrong chip / flash size errors | Bad target/board script |
| Second instance fails immediately | Port collision or missing `hla_serial` |
| Serial not matching | Escaping / wrong serial encoding for clone ST-Links |
