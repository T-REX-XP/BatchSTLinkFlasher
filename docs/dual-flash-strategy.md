# Dual flash strategy

How Batch ST-Link Flasher flashes **several ST-Link programmers at once** when
some probes have unique HLA serials and others are cheap clones that do not.

**Related:** `docs/openocd-integration.md` (CLI / ports), `docs/architecture.md`
(modules), `docs/stlink-clone-serial.md` (making clones unique via firmware),
`FR-FLASH-03` in `docs/requirements.md`.

---

## 1. Why two modes?

OpenOCD talks to ST-Link over USB using the **HLA** (High-Level Adapter) layer.
When more than one ST-Link is plugged in, OpenOCD must be told **which** probe
to open. That is done with:

```text
-c hla_serial "…"
```

| Probe | Typical serial | Can OpenOCD pin it? |
|-------|----------------|---------------------|
| Genuine ST-Link / unique iSerial | Hex / `\xNN…` | **Yes** → safe **parallel** flash |
| Many clones | Placeholder `%`, or Windows invents `5&…` | **No** → OpenOCD would grab an arbitrary probe |

If two clones both lack a usable `hla_serial`, starting two OpenOCD processes
at once races: both may attach to the same dongle, or the wrong target.

**Solution:** classify each selected adapter, then run:

1. **HLA-bound** adapters → **parallel** (one OpenOCD each, with `hla_serial`).
2. **Unbound clones** → **sequential**, with **Windows USB isolation** so only
   one ST-Link remains enabled while that OpenOCD runs **without** `hla_serial`.

---

## 2. Classification

Implemented in `FlashOrchestrator` via `can_bind_hla(adapter)`:

```text
multi_adapter_ok == true  AND  hla_serial is non-empty
        ↓
   HLA-bound (parallel)
        else
   unbound / clone (sequential + isolation)
```

Discovery fills `AdapterInfo`:

| Field | Role |
|-------|------|
| `serial` | Display / log id (`%`, Windows instance suffix, or real serial) |
| `hla_serial` | Value passed to OpenOCD (empty when not bindable) |
| `multi_adapter_ok` | `true` when discovery believes HLA binding is safe |
| `usb_path` | Full PnP instance id (`USB\VID_0483&PID_3748\…`) — **required** for clone isolation |

Clones that share display serial `%` are distinguished by `usb_path` (and by
orchestrator job keys `index:serial:usb_path`).

---

## 3. End-to-end flow

```mermaid
flowchart TD
  Start([Operator clicks Flash]) --> Split{Split selected adapters}
  Split -->|can_bind_hla| Bound[HLA-bound list]
  Split -->|else| Unbound[Unbound / clone list]

  Bound --> Par[Run all HLA jobs in parallel]
  Par --> EachHla["FlashJob × N\n• unique TCP ports\n• hla_serial set"]
  EachHla --> WaitHla[Join all HLA threads]

  WaitHla --> AnyClone{Unbound remaining\nand not cancelled?}
  Unbound --> AnyClone
  AnyClone -->|no| Done([OrchestratorSummary])
  AnyClone -->|yes| Seq[For each clone in order]

  Seq --> Iso["isolated_usb_device(target, siblings)\nDisable every other ST-Link PnP node"]
  Iso --> One["FlashJob × 1\n• no hla_serial\n• OpenOCD sees only target"]
  One --> Re["Re-enable siblings"]
  Re --> More{More clones?}
  More -->|yes| Seq
  More -->|no| Done
```

**Order matters:** HLA probes finish first (true parallel), then clones run
one-by-one. Mixed selections are supported.

---

## 4. Parallel path (originals / unique serial)

```mermaid
sequenceDiagram
  participant Orch as FlashOrchestrator
  participant J1 as FlashJob A
  participant J2 as FlashJob B
  participant OCD1 as OpenOCD A
  participant OCD2 as OpenOCD B

  Orch->>Orch: allocate_openocd_ports_batch(N)
  par Probe A
    Orch->>J1: start thread
    J1->>OCD1: openocd … hla_serial A … program …
    OCD1-->>J1: exit 0 / fail
    J1-->>Orch: result A
  and Probe B
    Orch->>J2: start thread
    J2->>OCD2: openocd … hla_serial B … program …
    OCD2-->>J2: exit 0 / fail
    J2-->>Orch: result B
  end
  Orch->>Orch: join threads
```

Properties:

- One OpenOCD **process per** adapter (never share a process across probes).
- Unique `gdb_port` / `telnet_port` / `tcl_port` triples (see openocd-integration).
- Failures are isolated per job; one bad cable does not stop siblings.

---

## 5. Sequential path (clones + USB isolation)

When OpenOCD cannot pin a probe, the app temporarily makes the target the
**only enabled ST-Link** on the machine (among known discovery results).

```mermaid
sequenceDiagram
  participant Orch as FlashOrchestrator
  participant CM as Config Manager
  participant OCD as OpenOCD
  participant T as Target clone
  participant S as Sibling ST-Links

  Orch->>CM: CM_Disable_DevNode(each sibling)
  Note over S: USB nodes disabled
  Orch->>OCD: openocd … (no hla_serial) program …
  OCD->>T: attach to only remaining probe
  OCD-->>Orch: exit code
  Orch->>CM: CM_Enable_DevNode(each sibling)
  Note over S: USB nodes restored
```

Isolation helper: `services/windows_device_control.py` → `isolated_usb_device`.

```text
siblings = known_adapters[].usb_path  (all discovered ST-Links)
target   = adapter.usb_path

for each sibling ≠ target:
    CM_Disable_DevNode(sibling)     # fail → DeviceIsolationError
run FlashJob (no hla_serial)
finally:
    CM_Enable_DevNode(every disabled sibling)
```

### Isolation timeline (two clones)

```text
 time →
 Clone1:  [==== disable siblings ====][==== flash ====][== re-enable ==]
 Clone2:                                                   [==== disable ====][==== flash ====][== re-enable ==]
 HLA A/B: [======== parallel flash (already done) ========]
```

---

## 6. Module map

```mermaid
flowchart LR
  UI[ui/workers.FlashWorker] --> Orch[flashing/orchestrator.py]
  Orch --> Bind{can_bind_hla?}
  Bind -->|yes| JobP[flashing/job.py × N parallel]
  Bind -->|no| Iso[windows_device_control.isolated_usb_device]
  Iso --> JobS[flashing/job.py × 1]
  JobP --> Cmd[flashing/openocd.py]
  JobS --> Cmd
  Cmd --> Proc[OpenOCD subprocess]
```

| Module | Responsibility |
|--------|----------------|
| `flashing/orchestrator.py` | Split bound/unbound; parallel then sequential |
| `flashing/job.py` | Run one OpenOCD job, stream logs, timeouts |
| `flashing/openocd.py` | Build argv (`hla_serial` only when set) |
| `services/windows_device_control.py` | Disable/enable PnP nodes |
| `services/windows_pnp.py` / `device_service.py` | Discovery → `AdapterInfo` + `usb_path` |

Identify LED reuses the same disable/enable APIs to blink the COM LED
(see openocd-integration).

---

## 7. Operator view

| Selection | What happens |
|-----------|----------------|
| 1+ unique-serial only | All flash together |
| 1+ clones only | One after another; others briefly disappear from Device Manager |
| Mix | Unique-serial group first (parallel), then each clone |
| Clone without `usb_path` | Row fails: cannot isolate |
| Disable denied by Windows | Job fails — try **Run as administrator**, unplug extras, or use unique-serial probes |

**Factory recommendation:** buy / program ST-Links with unique USB serials so
the whole batch stays in the parallel path (faster, no elevation, no Device
Manager flicker).

---

## 8. Failure modes

| Symptom | Cause | Mitigation |
|---------|--------|------------|
| Two clones selected, both flash the same board | Isolation skipped / failed | Ensure `usb_path` present; elevate; check Device Manager |
| `could not disable sibling ST-Link` | Permissions / driver holds node | Elevate app; close STM32CubeProgrammer / other OpenOCD |
| Sibling stays disabled after crash | Rare enable failure | Re-enable in Device Manager or unplug/replug |
| Parallel job opens wrong probe | Bad / empty `hla_serial` | Fix discovery / HLA normalization |

Cancel: HLA threads are cancelled; remaining sequential clones are skipped
(`cancelled before start`).

---

## 9. Code entry points

```text
FlashOrchestrator.run()
  └─ _execute()
       ├─ bound   → _run_parallel()
       └─ unbound → _run_sequential_isolated()
              └─ isolated_usb_device(target, sibling_ids)
                     └─ FlashJob.run()   # no hla_serial
```

Tests: `tests/test_orchestrator.py` (and related) cover split behavior with
mocked isolation / jobs.
