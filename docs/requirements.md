# Requirements — Batch ST-Link Flasher

> **Audience**: humans and AI agents. Treat this file as the product contract.
> Prefer this doc over chat history when implementing or changing behavior.

## 1. Goal

Desktop application that flashes **the same firmware file** onto **1–N STM32 (or compatible) targets** in parallel, each connected through its own **ST-Link V2** (or ST-Link V2-1) USB programmer, using **OpenOCD** as the programmer backend.

## 2. Non-goals (v1)

- Debugging / GDB sessions
- Different firmware per device in one run
- Automatic MCU detection beyond what OpenOCD/target config provides
- Bundling OpenOCD binaries in the installer (document external install; optional later)
- macOS / Linux as primary targets (design should not block them; Windows first)

## 3. Actors & environment

| Actor | Description |
|-------|-------------|
| Operator | Factory / lab user with 1–N ST-Links plugged into one Windows PC |
| OpenOCD | External CLI tool; must be on `PATH` or configured via app setting |
| Target MCU | Powered and wired to its ST-Link (SWD); family selected via OpenOCD target/board config |

**Assumptions**

- Each programmer has a unique USB serial (HLA serial) usable by OpenOCD (`hla_serial` / `adapter serial`).
- Operator knows (or selects) the correct OpenOCD interface + target/board scripts for the product under test.
- Firmware is a single file: `.elf`, `.hex`, or `.bin` (with base address when `.bin`).

## 4. Functional requirements

### 4.1 Device discovery

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-DISC-01 | Detect connected ST-Link V2 / V2-1 devices on USB | Must |
| FR-DISC-02 | Show count of programmers currently connected | Must |
| FR-DISC-03 | Per device show: display name, USB serial (HLA), VID/PID, path/bus info if available, OpenOCD-ready serial string | Must |
| FR-DISC-04 | Refresh discovery on demand (button) | Must |
| FR-DISC-05 | Optional auto-refresh while idle (interval configurable; default off or ≥2s) | Should |
| FR-DISC-06 | Mark devices that cannot be selected (missing serial, in use, unsupported) with a clear reason | Should |

### 4.2 Firmware & flash configuration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CFG-01 | User selects one firmware file (`.elf` / `.hex` / `.bin`) | Must |
| FR-CFG-02 | For `.bin`, user must provide flash base address (default `0x08000000`) | Must |
| FR-CFG-03 | User selects OpenOCD interface script (default ST-Link V2) and target/board script | Must |
| FR-CFG-04 | User can set path to `openocd` executable (persist in settings) | Must |
| FR-CFG-05 | User can select which discovered devices participate in the next flash run | Must |
| FR-CFG-06 | Persist last-used firmware path, target config, and OpenOCD path across sessions | Should |

### 4.3 Parallel flashing

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-FLASH-01 | Start flash on all selected devices in parallel (one OpenOCD process per device) | Must |
| FR-FLASH-02 | Assign unique OpenOCD TCP ports per process (`gdb_port`, `telnet_port`, `tcl_port`) to avoid collisions | Must |
| FR-FLASH-03 | Bind each process to exactly one adapter via serial (`hla_serial` or equivalent) | Must |
| FR-FLASH-04 | Per-device states: Idle → Queued → Running → Succeeded \| Failed \| Cancelled | Must |
| FR-FLASH-05 | Cancel all in-progress flashes | Must |
| FR-FLASH-06 | Cancel a single device’s flash | Should |
| FR-FLASH-07 | Do not start a new global flash while any flash is Running (or allow only if no overlap on same serial — v1: block) | Must |
| FR-FLASH-08 | After each device finishes, release its ports/process cleanly | Must |

### 4.4 Progress, logs, errors

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-LOG-01 | Per-device log panel (or filterable global log with device id prefix) | Must |
| FR-LOG-02 | Stream OpenOCD stdout/stderr into that device’s log in near real time | Must |
| FR-LOG-03 | Per-device progress: indeterminate while running, or parsed % if reliably available; always show elapsed time | Must |
| FR-LOG-04 | On failure, show exit code + last meaningful OpenOCD error line in UI | Must |
| FR-LOG-05 | Summary bar: N succeeded / N failed / N running | Must |
| FR-LOG-06 | Export session logs to a text/JSON file | Should |

### 4.5 UX (desktop)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UX-01 | Single main window: device list + config + start/cancel + logs | Must |
| FR-UX-02 | Clear validation before Start (OpenOCD found, file exists, ≥1 device, target config set) | Must |
| FR-UX-03 | Keyboard: Start / Cancel shortcuts documented in UI or Help | Could |

## 5. Non-functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-01 | Primary OS: Windows 10/11 x64 | Must |
| NFR-02 | Support at least **8** concurrent ST-Links without UI freeze | Must |
| NFR-03 | UI remains responsive during flash (worker threads / async; no OpenOCD on UI thread) | Must |
| NFR-04 | Failures on one device must not stop others | Must |
| NFR-05 | Settings stored under user app data (not next to exe only) | Should |
| NFR-06 | Changelog maintained in repo root `CHANGELOG.md` | Must |
| NFR-07 | Code and docs suitable for AI-assisted development (see `AGENTS.md`) | Must |

## 6. Tech stack (decided)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | **Python 3.11+** | Fast to iterate; excellent subprocess orchestration; AI-friendly |
| UI | **PySide6 (Qt)** | Mature desktop UX; signals/slots for device/job updates |
| Programmer | **OpenOCD** (external) | Existing ST-Link support; multi-adapter via serial + unique ports |
| Device enum | Prefer **`st-info --probe`** if available; fallback **pyusb** (VID `0x0483`) | Serial strings needed for OpenOCD |
| Packaging (later) | PyInstaller or similar | Single-folder Windows distribute |

Do **not** change stack without updating `docs/architecture.md` and this section.

## 7. Acceptance criteria (v1)

1. With 2+ ST-Links connected, the app lists each with a distinct serial.
2. Operator selects one `.hex`/`.elf`, chooses target config, selects all devices, clicks Flash.
3. Each device runs its own OpenOCD job; UI shows per-device Running → Succeeded/Failed.
4. One intentional failure (wrong target, no MCU) does not cancel siblings.
5. Cancel stops remaining OpenOCD processes.
6. `CHANGELOG.md` has an Unreleased / version entry describing the feature set.

## 8. Open questions (resolve before coding these areas)

| # | Question | Default if unanswered |
|---|----------|------------------------|
| Q1 | Exact MCU families in production? | Configurable OpenOCD `target`/`board` scripts only |
| Q2 | Must verify flash (read-back / CRC)? | v1: rely on OpenOCD program + verify flags if available |
| Q3 | Ship OpenOCD with the app? | No — require install + path setting |
| Q4 | RDP / option-byte programming? | Out of scope v1 |

## 9. Doc map

| File | Purpose |
|------|---------|
| `docs/requirements.md` | This contract |
| `docs/architecture.md` | Components, data flow, module layout |
| `docs/plan.md` | Phased implementation checklist for agents/humans |
| `docs/openocd-integration.md` | CLI recipes, ports, serial binding |
| `AGENTS.md` | How AI agents must work in this repo |
| `CHANGELOG.md` | User-visible change history |
| `README.md` | Install, run, operator quick start |
