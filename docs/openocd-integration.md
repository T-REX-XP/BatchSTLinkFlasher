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

Parse each probe block for `serial:` and any OpenOCD hex/`hla` hint. Pass the form OpenOCD expects (ASCII serial or `\xNN` escaped bytes for older clones).

### Fallback: wrong serial + debug log

```text
openocd -d3 -f interface/stlink.cfg -f target/stm32f1x.cfg -c "hla_serial wrong_serial"
```

Search log for `Device serial number '…' doesn't match`.

### Fallback: pyusb

Filter `idVendor == 0x0483` and ST-Link PIDs (e.g. `0x3748` V2, `0x374B` V2-1, others as needed). Read USB string descriptor iSerial.

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
