# Architecture

## 1. Overview

```
┌─────────────────────────────────────────────────────────┐
│  UI (PySide6)                                           │
│  DeviceTable | ConfigPanel | FlashControls | LogView    │
└───────────────┬─────────────────────────────┬───────────┘
                │ signals / slots             │
┌───────────────▼─────────────┐   ┌───────────▼───────────┐
│  DeviceService              │   │  FlashOrchestrator    │
│  - enumerate ST-Links       │   │  - HLA parallel       │
│  - map to AdapterInfo       │   │  - clone sequential   │
│  - usb_path / HLA flags     │   │  - USB isolation      │
└───────────────┬─────────────┘   └───────────┬───────────┘
                │                             │
                │                  ┌──────────▼──────────┐
                │                  │ FlashJob (per device)│
                │                  │ - build OpenOCD cmd │
                │                  │ - stream logs       │
                │                  │ - track state       │
                │                  └──────────┬──────────┘
                │                             │
┌───────────────▼─────────────────────────────▼───────────┐
│  OpenOCDProcess (subprocess)  × N                       │
│  HLA: -c "hla_serial …"   clones: no serial + isolation │
│  unique ports + program/verify                             │
└─────────────────────────────────────────────────────────┘
```

Dual flash strategy (diagrams): [`docs/dual-flash-strategy.md`](dual-flash-strategy.md).

## 2. Package layout

```
src/batch_stlink_flasher/
  __init__.py          # package version
  __main__.py          # python -m batch_stlink_flasher
  app.py               # QApplication bootstrap
  bundled_tools.py     # locate tools/openocd next to frozen EXE
  assets_util.py
  assets/              # logo.png, app_icon.png/.ico, splash.png
  ui/
    main_window.py     # 3-pane splitter (devices / config / log); compact laptop layout
    about_dialog.py
    splash_screen.py
    theme.py
    flow_layout.py     # wrapping toolbar
    device_table.py    # resizable columns; narrow-width column hide
    config_panel.py    # primary + collapsible Advanced
    log_view.py
    workers.py
  services/
    device_service.py  # discovery
    windows_pnp.py     # Windows USB enum + port location
    windows_device_control.py  # disable/enable PnP (clone isolation)
    identify.py        # Identify LED blink
    settings.py        # QSettings / JSON persistence
  flashing/
    models.py          # AdapterInfo, FlashConfig, JobState
    orchestrator.py    # dual strategy: HLA parallel + clone sequential
    job.py
    openocd.py         # command builder + process wrapper
  util/
    ports.py           # allocate free TCP ports
    logging_setup.py
    win_process.py
```

## 3. Core models

```python
@dataclass(frozen=True)
class AdapterInfo:
    serial: str              # human / st-info serial (may be "%" on clones)
    hla_serial: str          # string passed to OpenOCD (empty if unbound)
    vid: int
    pid: int
    product: str
    manufacturer: str
    usb_path: str | None     # full PnP instance id
    usb_port: int | None     # from LocationInformation Port_#N
    usb_hub: int | None      # from LocationInformation Hub_#M
    multi_adapter_ok: bool   # True when HLA parallel binding is safe
    skip_reason: str | None

class JobState(Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class FlashConfig:
    openocd_path: Path
    firmware_path: Path
    interface_cfg: str       # e.g. interface/stlink.cfg
    target_cfg: str          # e.g. target/stm32f1x.cfg
    bin_base_address: int | None  # required for .bin
```

## 4. OpenOCD process rules

1. **One process per adapter** — never share an OpenOCD instance across devices.
2. **Serial binding** — HLA-capable adapters always pass ``hla_serial``. Clones
   without a unique serial flash under Windows USB isolation instead (see
   [`dual-flash-strategy.md`](dual-flash-strategy.md)).
3. **Unique ports** — for job index `i`, allocate three free ports (or fixed base + offsets): `gdb`, `telnet`, `tcl`. Prefer `tcl_port disabled` / `0` if supported by the installed OpenOCD to reduce conflicts.
4. **Working directory** — OpenOCD scripts path must resolve (`-s` search path if needed).
5. **Program sequence** (typical):
   - init / halt
   - `program <file> [address] verify reset exit`
6. **Timeouts** — configurable soft timeout per job (default e.g. 120s); on timeout kill process → Failed.

Details and example CLI: `docs/openocd-integration.md`.

## 5. Threading model

- **UI thread**: widgets only.
- **Discovery**: `DiscoveryWorker` (`QThread`); emit adapters list.
- **Identify LED**: `IdentifyWorker` — PnP disable/enable off the UI thread.
- **Flash jobs**: `FlashWorker` runs `FlashOrchestrator`; stdout/stderr → queued signals → UI.
- **Orchestrator**: HLA jobs on threads in parallel; clones sequential with isolation.

Never call blocking USB/OpenOCD APIs on the UI thread.

## 6. Settings

Persist with `QSettings` (org=`BatchSTLinkFlasher`, app=`BatchSTLinkFlasher`):

- `openocd_path`
- `last_firmware_path`
- `interface_cfg`, `target_cfg`
- `bin_base_address`
- `job_timeout_sec`
- `theme_mode` (system / light / dark)

## 7. Error taxonomy

| Source | UI treatment |
|--------|--------------|
| OpenOCD not found | Block Start; show path error |
| No adapters | Block Start |
| Missing serial / not selectable | Device row disabled + reason |
| Clone isolation failed | Device Failed + elevate / unplug hint |
| Process non-zero exit | Device Failed + last error line |
| Timeout | Kill + Failed |
| Cancel | Cancelled (not counted as Failed) |

## 8. Extensibility (later)

- Alternate backends (`st-flash`) behind a `ProgrammerBackend` protocol
- Per-device firmware mapping
- Optional “always sequential” operator override (HLA included)
