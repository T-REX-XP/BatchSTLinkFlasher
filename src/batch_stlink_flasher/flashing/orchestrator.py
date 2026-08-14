"""Parallel flash orchestration across adapters."""

from __future__ import annotations

import threading
from collections.abc import Callable
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


class FlashOrchestrator:
    """
    Flash N adapters in parallel (one OpenOCD process / unique ports each).

    One job failing or being cancelled does not abort siblings.
    """

    def __init__(
        self,
        adapters: list[AdapterInfo],
        config: FlashConfig,
        *,
        on_line: JobLineCallback | None = None,
        on_job_done: JobDoneCallback | None = None,
    ) -> None:
        if not adapters:
            raise ValueError("adapters must not be empty")
        self.adapters = list(adapters)
        self.config = config
        self.on_line = on_line
        self.on_job_done = on_job_done

        self._lock = threading.Lock()
        self._running = False
        self._jobs: dict[str, FlashJob] = {}
        self._results: dict[str, FlashJobResult] = {}

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def cancel_all(self) -> None:
        """Cancel every in-flight job."""
        with self._lock:
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
        Start all jobs and block until they finish.

        Raises ``RuntimeError`` if a run is already in progress.
        """
        with self._lock:
            if self._running:
                raise RuntimeError("a flash run is already in progress")
            self._running = True
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
        runnable: list[tuple[str, AdapterInfo]] = []

        multi = len(self.adapters) > 1
        for index, adapter in enumerate(self.adapters):
            key = _adapter_key(adapter, index)
            if multi and not _can_bind_serial(adapter):
                result = FlashJobResult(
                    state=JobState.FAILED,
                    exit_code=None,
                    elapsed_sec=0.0,
                    argv=[],
                    log_lines=[],
                    error_summary=(
                        "adapter lacks a usable HLA serial; cannot flash in parallel "
                        "with other probes (clone serial placeholder?)"
                    ),
                )
                with self._lock:
                    self._results[key] = result
                if self.on_job_done is not None:
                    self.on_job_done(adapter, result)
            else:
                runnable.append((key, adapter))

        if runnable:
            port_triples = allocate_openocd_ports_batch(len(runnable))
            threads: list[threading.Thread] = []

            for (key, adapter), ports in zip(runnable, port_triples, strict=True):
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

        ordered: list[AdapterJobResult] = []
        with self._lock:
            stored = dict(self._results)

        for index, adapter in enumerate(self.adapters):
            key = _adapter_key(adapter, index)
            result = stored.get(key)
            if result is None:
                result = FlashJobResult(
                    state=JobState.FAILED,
                    exit_code=None,
                    elapsed_sec=0.0,
                    error_summary="missing job result",
                )
            ordered.append(AdapterJobResult(adapter=adapter, result=result))

        return OrchestratorSummary(results=ordered)

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
        with self._lock:
            self._results[key] = result
            self._jobs.pop(key, None)
        if self.on_job_done is not None:
            self.on_job_done(adapter, result)

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


def _can_bind_serial(adapter: AdapterInfo) -> bool:
    return bool(adapter.multi_adapter_ok and (adapter.hla_serial or "").strip())
