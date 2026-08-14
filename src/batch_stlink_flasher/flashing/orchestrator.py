"""Parallel flash orchestration across adapters."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from batch_stlink_flasher.flashing.job import FlashJob, FlashJobResult, LineCallback
from batch_stlink_flasher.flashing.models import AdapterInfo, FlashConfig, JobState
from batch_stlink_flasher.util.ports import allocate_openocd_ports_batch

JobDoneCallback = Callable[[AdapterInfo, FlashJobResult], None]
JobLineCallback = Callable[[AdapterInfo, str], None]


@dataclass
class AdapterJobResult:
    """Per-adapter outcome from an orchestrator run."""

    adapter: AdapterInfo
    result: FlashJobResult


@dataclass
class OrchestratorSummary:
    """Aggregate counts after ``FlashOrchestrator.run()`` completes."""

    results: list[AdapterJobResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.result.state == JobState.SUCCEEDED)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.result.state == JobState.FAILED)

    @property
    def cancelled(self) -> int:
        return sum(1 for r in self.results if r.result.state == JobState.CANCELLED)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_succeeded(self) -> bool:
        return self.total > 0 and self.succeeded == self.total


def can_bind_hla(adapter: AdapterInfo) -> bool:
    """True when OpenOCD can pin this probe with ``hla_serial`` (genuine / unique)."""
    return bool(adapter.multi_adapter_ok and (adapter.hla_serial or "").strip())


class FlashOrchestrator:
    """
    Flash N adapters with a dual strategy:

    * **HLA-bound** (unique serial): all in parallel, each with ``hla_serial``.
    * **Unbound** (clone placeholder serial): one-at-a-time, temporarily
      disabling sibling ST-Link USB nodes so OpenOCD attaches to only that probe.

    HLA jobs run first (parallel), then unbound jobs (sequential + isolation),
    unless ``force_sequential`` is set (one adapter at a time for all).
    """

    def __init__(
        self,
        adapters: list[AdapterInfo],
        config: FlashConfig,
        *,
        on_line: JobLineCallback | None = None,
        on_job_done: JobDoneCallback | None = None,
        known_adapters: Sequence[AdapterInfo] | None = None,
        force_sequential: bool = False,
    ) -> None:
        if not adapters:
            raise ValueError("adapters must not be empty")
        self.adapters = list(adapters)
        self.config = config
        self.on_line = on_line
        self.on_job_done = on_job_done
        # Full discovery set — used to disable non-target ST-Links for clones.
        self.known_adapters = list(known_adapters) if known_adapters is not None else list(adapters)
        self.force_sequential = force_sequential

        self._lock = threading.Lock()
        self._running = False
        self._jobs: dict[str, FlashJob] = {}
        self._results: dict[str, FlashJobResult] = {}
        self._cancel_requested = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def cancel_all(self) -> None:
        """Cancel every in-flight job and skip remaining sequential work."""
        with self._lock:
            self._cancel_requested = True
            jobs = list(self._jobs.values())
        for job in jobs:
            job.cancel()

    def cancel_adapter(self, serial: str) -> bool:
        """
        Cancel job(s) whose ``adapter.serial`` matches.

        Returns True if at least one running job was signalled.
        """
        with self._lock:
            jobs = [job for job in self._jobs.values() if job.adapter.serial == serial]
        if not jobs:
            return False
        for job in jobs:
            job.cancel()
        return True

    def run(self) -> OrchestratorSummary:
        """
        Start jobs and block until they finish.

        Raises ``RuntimeError`` if a run is already in progress.
        """
        with self._lock:
            if self._running:
                raise RuntimeError("a flash run is already in progress")
            self._running = True
            self._cancel_requested = False
            self._jobs.clear()
            self._results.clear()

        try:
            return self._execute()
        finally:
            with self._lock:
                self._running = False
                self._jobs.clear()

    def _execute(self) -> OrchestratorSummary:
        self.config.validate()

        bound: list[tuple[str, AdapterInfo]] = []
        unbound: list[tuple[str, AdapterInfo]] = []
        for index, adapter in enumerate(self.adapters):
            key = _adapter_key(adapter, index)
            if can_bind_hla(adapter):
                bound.append((key, adapter))
            else:
                unbound.append((key, adapter))

        if self.force_sequential:
            # One at a time: HLA keeps hla_serial; clones still isolate siblings.
            for key, adapter in bound + unbound:
                if self._is_cancelled():
                    break
                if can_bind_hla(adapter):
                    self._run_parallel([(key, adapter)])
                else:
                    self._run_sequential_isolated([(key, adapter)])
        else:
            if bound:
                self._run_parallel(bound)

            if unbound and not self._is_cancelled():
                self._run_sequential_isolated(unbound)

        ordered: list[AdapterJobResult] = []
        with self._lock:
            stored = dict(self._results)

        for index, adapter in enumerate(self.adapters):
            key = _adapter_key(adapter, index)
            result = stored.get(key)
            if result is None:
                if self._is_cancelled():
                    result = FlashJobResult(
                        state=JobState.CANCELLED,
                        exit_code=None,
                        elapsed_sec=0.0,
                        error_summary="cancelled before start",
                    )
                else:
                    result = FlashJobResult(
                        state=JobState.FAILED,
                        exit_code=None,
                        elapsed_sec=0.0,
                        error_summary="missing job result",
                    )
            ordered.append(AdapterJobResult(adapter=adapter, result=result))

        return OrchestratorSummary(results=ordered)

    def _run_parallel(self, items: list[tuple[str, AdapterInfo]]) -> None:
        port_triples = allocate_openocd_ports_batch(len(items))
        threads: list[threading.Thread] = []

        for (key, adapter), ports in zip(items, port_triples, strict=True):
            job = FlashJob(
                adapter,
                self.config,
                ports=ports,
                on_line=self._make_line_callback(adapter),
            )
            job.mark_queued()
            with self._lock:
                self._jobs[key] = job

            thread = threading.Thread(
                target=self._run_one,
                args=(key, adapter, job),
                name=f"flash-{key}",
                daemon=True,
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def _run_sequential_isolated(self, items: list[tuple[str, AdapterInfo]]) -> None:
        from batch_stlink_flasher.services.windows_device_control import (
            DeviceIsolationError,
            isolated_usb_device,
        )

        sibling_ids = [
            a.usb_path
            for a in self.known_adapters
            if a.usb_path
        ]

        for key, adapter in items:
            if self._is_cancelled():
                self._store_result(
                    key,
                    adapter,
                    FlashJobResult(
                        state=JobState.CANCELLED,
                        exit_code=None,
                        elapsed_sec=0.0,
                        error_summary="cancelled before start",
                    ),
                )
                continue

            target_id = (adapter.usb_path or "").strip()
            if not target_id:
                self._store_result(
                    key,
                    adapter,
                    FlashJobResult(
                        state=JobState.FAILED,
                        exit_code=None,
                        elapsed_sec=0.0,
                        error_summary=(
                            "clone/unbound adapter has no USB instance id; "
                            "cannot isolate for multi-adapter flash"
                        ),
                    ),
                )
                continue

            ports = allocate_openocd_ports_batch(1)[0]
            job = FlashJob(
                adapter,
                self.config,
                ports=ports,
                on_line=self._make_line_callback(adapter),
            )
            job.mark_queued()
            with self._lock:
                self._jobs[key] = job

            try:
                with isolated_usb_device(target_id, sibling_ids):
                    if self._is_cancelled():
                        job.cancel()
                    result = job.run()
            except DeviceIsolationError as exc:
                result = FlashJobResult(
                    state=JobState.FAILED,
                    exit_code=None,
                    elapsed_sec=0.0,
                    error_summary=str(exc),
                )
            except Exception as exc:  # noqa: BLE001
                result = FlashJobResult(
                    state=JobState.FAILED,
                    exit_code=None,
                    elapsed_sec=0.0,
                    error_summary=f"job crashed: {exc}",
                )
            finally:
                with self._lock:
                    self._jobs.pop(key, None)

            self._store_result(key, adapter, result)

    def _run_one(self, key: str, adapter: AdapterInfo, job: FlashJob) -> None:
        try:
            result = job.run()
        except Exception as exc:  # noqa: BLE001 — isolate sibling failures
            result = FlashJobResult(
                state=JobState.FAILED,
                exit_code=None,
                elapsed_sec=0.0,
                error_summary=f"job crashed: {exc}",
            )
        self._store_result(key, adapter, result)
        with self._lock:
            self._jobs.pop(key, None)

    def _store_result(self, key: str, adapter: AdapterInfo, result: FlashJobResult) -> None:
        with self._lock:
            self._results[key] = result
        if self.on_job_done is not None:
            self.on_job_done(adapter, result)

    def _is_cancelled(self) -> bool:
        with self._lock:
            return self._cancel_requested

    def _make_line_callback(self, adapter: AdapterInfo) -> LineCallback | None:
        if self.on_line is None:
            return None

        def _cb(line: str) -> None:
            assert self.on_line is not None
            self.on_line(adapter, line)

        return _cb


def _adapter_key(adapter: AdapterInfo, index: int) -> str:
    """Stable key even when multiple clones share serial ``%``."""
    return f"{index}:{adapter.serial}:{adapter.usb_path or ''}"


# Back-compat alias used by older tests / callers.
_can_bind_serial = can_bind_hla
