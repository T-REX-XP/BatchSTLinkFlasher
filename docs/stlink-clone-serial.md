# ST-Link V2 clones — USB serial conflicts, repos, and approaches

Operator / lab notes for **cheap aluminum “ST-Link V2” dongles** that share the same
USB identity and break multi-probe setups.

**Source notes:** distilled from `docs/stlink.pdf` (Ukrainian Q&A on clone USB
conflicts) plus verified GitHub repos used by the community.

**Related in this project**

| Doc | Relevance |
|-----|-----------|
| [`docs/dual-flash-strategy.md`](dual-flash-strategy.md) | How **Batch ST-Link Flasher** runs clones **without** unique serials (sequential + USB isolation) |
| [`docs/openocd-integration.md`](openocd-integration.md) | `hla_serial`, ports, OpenOCD CLI |
| App UI | **Identify LED**, **USB port** column, Note `clone · sequential` |

> **Default recommendation for this app:** you do **not** need to reflash clones.
> Isolation already allows multi-clone flashing. Change serials only if you want
> **true parallel** HLA binding or to fix Windows Device Manager Code 10/43 on one hub.

---

## 1. Problem

Operating systems distinguish USB devices by **VID + PID + serial** (`iSerial`).

| Fact | Effect |
|------|--------|
| Clones often ship with the **same** flash image | Identical `iSerial` (or placeholder `%`) |
| Two identical serials on the **same USB root hub** | Driver routing conflict → Code **10** / **43**, flaky enumeration |
| Same clones on **different motherboard root hubs** | Sometimes “works” — OS can isolate them by controller |
| Passive USB hubs | Extra risk: power brown-out (≤500 mA/port class), not only serial collision |

Inside the stick the MCU is usually **STM32F103C8T6** or a Chinese analogue
(**Geehy APM32F103**, **CKS32/CS32**, **MH2103A**, …). Firmware may ignore the chip
UID and return a hard-coded serial string.

**Batch ST-Link Flasher** treats non-bindable serials as clones (`multi_adapter_ok=false`)
and flashes them one-by-one under Windows PnP isolation — see dual-flash strategy.

---

## 2. Identify what you have (no soldering)

Connect **one** probe at a time.

### Windows

1. Device Manager → Universal Serial Bus devices / controllers  
2. ST-Link / USB Composite Device → Properties → **Details**  
3. Property: **Device instance path**  
4. Value looks like: `USB\VID_0483&PID_3748\<SERIAL>`  
5. The segment after the last `\` is the USB serial Windows uses

Also useful: `st-info --probe` ([stlink-org/stlink](https://github.com/stlink-org/stlink)).

### Linux

```bash
dmesg | tail -n 30
lsusb -d 0483: -v | grep -i iSerial
```

### macOS

Apple menu → About This Mac → System Report → USB → ST-Link / STM32 → Serial Number.

### For OpenOCD / this app

Many V2 clones expose **binary** serials that look like garbage in `lsusb`. Tools:

| Tool | Repo | Use |
|------|------|-----|
| `st-info --probe` | [stlink-org/stlink](https://github.com/stlink-org/stlink) | Prints serial + OpenOCD-style string |
| `gethla` | [a-v-s/gethla](https://github.com/a-v-s/gethla) | Small C helper: dumps `\xNN…` for `hla_serial` |
| This app | discovery + HLA normalize | Sets `hla_serial` when bindable; else clone path |

---

## 3. Approaches (choose one)

Risk increases downward. Prefer the first options that meet your goal.

```text
┌─────────────────────────────────────────────────────────────┐
│ Goal: multi-clone flash in Batch ST-Link Flasher            │
│ → Approach A (do nothing hardware-wise)                     │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Goal: parallel OpenOCD / unique Windows IDs on one hub      │
│ → Approach B (official upgrade) or C (SWD + clean BL)       │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Goal: VCP / MSD / CMSIS-DAP / J-Link features               │
│ → Approach D (convert firmware: V2.1 / DAPLink / BMP / JL)  │
└─────────────────────────────────────────────────────────────┘
```

### Approach A — Use this app’s clone isolation (preferred here)

- No case opening, no second programmer.
- Select clones → Flash → HLA probes run in parallel; clones run **sequential + isolate**.
- Distinguish sticks with **Identify LED** and **USB port / hub** columns.

See [`docs/dual-flash-strategy.md`](dual-flash-strategy.md).

### Approach B — Official ST-Link firmware upgrade (USB only)

- Tool: [STSW-LINK007](https://www.st.com/en/development-tools/stsw-link007.html) / STM32CubeProgrammer firmware upgrade.
- May improve serial stability on some units; **often does nothing useful on cheap clones**.
- Risk: brick / “unknown device” on non-ST dies (Geehy / MH2103A CPUID differs).

### Approach C — SWD reflash: clean bootloader → ST upgrade (unique serial)

**Best permanent fix** when you need unique `iSerial` while keeping ST-Link behaviour.

1. Open the aluminum case; find 4 pads near USB: **3.3V, GND, SWCLK, SWDIO**.  
   **Pinout on silk/case varies** — always verify markings (SWDIO/SWCLK/SWIM).
2. Use a **second working** ST-Link as the programmer (target clone **not** on USB, or power carefully).
3. Unlock / mass-erase (RDP Level 1 is common) with OpenOCD, e.g.:

   ```bash
   openocd -f interface/stlink.cfg -f target/stm32f1x.cfg \
     -c "init" -c "halt" -c "stm32f1x unlock 0" -c "shutdown"
   ```

   For some clones OpenOCD expects a different `CPUTAPID` (e.g. `0x2ba01477`) —
   copy `stm32f1x.cfg` and adjust (see repair toolkit README).
4. Flash an **unprotected** ST-Link V2.1-style bootloader at `0x08000000`.
5. Plug the clone into USB alone; run **ST-Link Upgrade** / CubeProgrammer so application
   firmware is written and a **new serial** is derived from chip UID.

**Repos / guides**

| Repo | What it provides |
|------|------------------|
| [Zelmoghazy/st-link-v2-clone](https://github.com/Zelmoghazy/st-link-v2-clone) | Clone recovery, `Unprotected-2-1-Bootloader.bin`, OpenOCD notes; also J-Link conversion path |
| [bruinformula/STLINKV2-1-Cloning-Suite](https://github.com/bruinformula/STLINKV2-1-Cloning-Suite) | Suite + Electron helper to flash unprotected BL then ST updaters → V2.1 (+VCP/MSD) |
| [mike-pittelko/stlink-v2-repair-and-toolkit](https://github.com/mike-pittelko/stlink-v2-repair-and-toolkit) | Unlock recipes, TAPID tips, recovery workflow |
| [Krakenw/Stlink-Bootloaders](https://github.com/Krakenw/Stlink-Bootloaders) | Protected vs unprotected bootloader dumps (reference) |
| [GabyPCgeeK/stlink-tool](https://github.com/GabyPCgeeK/stlink-tool) | libusb tool to probe / flash ST-Link DFU payloads (advanced) |

### Approach D — Convert to another probe firmware

| Target | Repo / project | Notes |
|--------|----------------|-------|
| **DAPLink** (MSC + CDC + HID) | [ARMmbed/DAPLink](https://github.com/ARMmbed/DAPLink), forks e.g. [abigpad/DAPLink-STM](https://github.com/abigpad/DAPLink-STM) | Unique IDs; **not** ST-Link protocol — OpenOCD/CMSIS-DAP configs change; this app expects ST-Link/OpenOCD HLA |
| **Black Magic Probe** | [blackmagic-debug/blackmagic](https://github.com/blackmagic-debug/blackmagic) | GDB server on device; different workflow |
| **Segger J-Link** (OB) | Via [Zelmoghazy/st-link-v2-clone](https://github.com/Zelmoghazy/st-link-v2-clone) (STLinkReflash path) | License/ToS sensitive; easy to brick; keep a recovery stick |

If you convert away from ST-Link, **Batch ST-Link Flasher will not drive that probe** until/unless backends are extended.

### Approach E — Mythical “USB serial changer” scripts

Some write-ups mention a Python tool named **`stlink-v2-sn-changer`**. There is **no well-maintained, trusted canonical repo** that reliably rewrites clone serials over USB alone for all stick variants. Serials are typically baked into firmware or derived from UID after a proper bootloader+upgrade cycle (**Approach C**).

Do not rely on random “SN changer” binaries from unverified sources.

---

## 4. Hardware checklist

| Check | Why |
|-------|-----|
| MCU marking: STM32F103 vs APM32 / MH2103A / … | CPUID / unlock scripts differ; ST updater may reject analogues |
| Case pin silk for SWDIO/SWCLK/SWIM | Wrong wiring damages target or clone |
| Powered USB hub if using many sticks | Separates power issues from serial issues |
| One stick during upgrade / unlock | Avoid patching the wrong device |

---

## 5. How this maps to Batch ST-Link Flasher

| Probe after change | App behaviour |
|--------------------|---------------|
| Unique HLA serial | `multi_adapter_ok=true` → **parallel** OpenOCD with `hla_serial` |
| Still `%` / unbound | Clone path → **sequential + isolation** |
| Converted to DAPLink / BMP / J-Link | Not supported as ST-Link backend today |

Discovery still lists clones by **USB instance path** even when serials collide — that is intentional.

---

## 6. Safety / legal

- Unlocking RDP **erases** the probe firmware.
- Always keep **two** sticks so one can recover the other.
- Official ST firmware and Segger tools have license terms; community “clone to J-Link” guides are third-party and unsupported by this project.
- This document does **not** ship bootloader binaries — fetch them from the linked repos yourself.

---

## 7. Quick decision

| Situation | Do this |
|-----------|---------|
| Just need batch flash of N clones | Use the app (Approach A) |
| Windows hates two clones on one hub | Powered hub **or** Approach C |
| Want parallel HLA speed | Approach C (unique serials) or buy genuine / Nucleo probes |
| Want VCP + MSD | Approach C → V2.1 suite, or Approach D DAPLink (app won’t use it yet) |
