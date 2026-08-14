"""Single-device flash job lifecycle."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TextIO

from batch_stlink_flasher.flashing.models import (
    AdapterInfo,
    FlashConfig,
    JobState,
    OpenOcdPorts,
)
from batch_stlink_flasher.flashing.openocd import (
    build_openocd_command,
    summarize_openocd_error,
)
from batch_stlink_flasher.util.ports import allocate_openocd_ports
from batch_stlink_flasher.util.win_process import hidden_subprocess_kwargs

LineCallback = Callable[[str], None]


@dataclass
class FlashJobResult:
    """Outcome of one ``FlashJob.run()``."""

    state: JobState
    exit_code: int | None
    elapsed_sec: float
    argv: list[str] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)
    error_summary: str | None = None


class FlashJob:
    """
    Run one OpenOCD flash for a single adapter.

    ``run()`` is blocking. Call ``cancel()`` from another thread to request stop.
    """

    def __init__(
        self,
        adapter: AdapterInfo,
        config: FlashConfig,
        *,
        ports: OpenOcdPorts | None = None,
        on_line: LineCallback | None = None,
    ) -> None:
        self.adapter = adapter
        self.config = config
        self.ports = ports
        self.on_line = on_line
        self._state = JobState.IDLE
        self._cancel = threading.Event()
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> JobState:
        return self._state

    def cancel(self) -> None:
        """Request cancellation; kills the OpenOCD process if running."""
        self._cancel.set()
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            _terminate_process(proc)

    def mark_queued(self) -> None:
        """Move IDLE → QUEUED before the orchestrator starts the worker thread."""
        if self._state != JobState.IDLE:
            raise RuntimeError(f"FlashJob cannot queue from state {self._state}")
        self._state = JobState.QUEUED

    def run(self) -> FlashJobResult:
        """Start OpenOCD, stream logs, and map the exit to a terminal ``JobState``."""
        if self._state not in {JobState.IDLE, JobState.QUEUED}:
            raise RuntimeError(f"FlashJob cannot run from state {self._state}")

        self.config.validate()
        ports = self.ports or allocate_openocd_ports()

        # Bind HLA only when the adapter has a usable serial (multi-adapter safe).
        hla_arg: str | None = None
        if self.adapter.multi_adapter_ok and (self.adapter.hla_serial or "").strip():
            hla_arg = self.adapter.hla_serial.strip()

        argv = build_openocd_command(self.config, hla_arg, ports)
        log_lines: list[str] = []
        self._state = JobState.RUNNING
        self._cancel.clear()
        started = time.monotonic()

        try:
            proc = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **hidden_subprocess_kwargs(),
            )
        except OSError as exc:
            self._state = JobState.FAILED
            summary = f"failed to start OpenOCD: {exc}"
            return FlashJobResult(
                state=JobState.FAILED,
                exit_code=None,
                elapsed_sec=time.monotonic() - started,
                argv=argv,
                log_lines=[summary],
                error_summary=summary,
            )

        with self._lock:
            self._proc = proc

        assert proc.stdout is not None
        reader = threading.Thread(
            target=_drain_stdout,
            args=(proc.stdout, log_lines, self.on_line),
            name="openocd-stdout",
            daemon=True,
        )
        reader.start()

        timed_out = False
        exit_code: int | None = None
        try:
            exit_code = self._wait_for_exit(proc, timeout_sec=self.config.job_timeout_sec)
            if exit_code is None and self._cancel.is_set():
                _terminate_process(proc)
                exit_code = proc.poll()
            elif exit_code is None:
                timed_out = True
                _terminate_process(proc)
                exit_code = proc.poll()
        finally:
            reader.join(timeout=5.0)
            with self._lock:
                self._proc = None

        elapsed = time.monotonic() - started

        if self._cancel.is_set() and not timed_out:
            self._state = JobState.CANCELLED
            return FlashJobResult(
                state=JobState.CANCELLED,
                exit_code=exit_code,
                elapsed_sec=elapsed,
                argv=argv,
                log_lines=list(log_lines),
                error_summary="cancelled",
            )

        if timed_out:
            self._state = JobState.FAILED
            summary = f"timed out after {self.config.job_timeout_sec:g}s"
            return FlashJobResult(
                state=JobState.FAILED,
                exit_code=exit_code,
                elapsed_sec=elapsed,
                argv=argv,
                log_lines=list(log_lines),
                error_summary=summary,
            )

        if exit_code == 0:
            self._state = JobState.SUCCEEDED
            return FlashJobResult(
                state=JobState.SUCCEEDED,
                exit_code=0,
                elapsed_sec=elapsed,
                argv=argv,
                log_lines=list(log_lines),
                error_summary=None,
            )

        self._state = JobState.FAILED
        summary = summarize_openocd_error(log_lines, exit_code=exit_code)
        return FlashJobResult(
            state=JobState.FAILED,
            exit_code=exit_code,
            elapsed_sec=elapsed,
            argv=argv,
            log_lines=list(log_lines),
            error_summary=summary,
        )

    def _wait_for_exit(self, proc: subprocess.Popen[str], *, timeout_sec: float) -> int | None:
        """Wait until process exits, cancel, or timeout. Return exit code or None."""
        deadline = time.monotonic() + timeout_sec
        while True:
            if self._cancel.is_set():
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                return proc.wait(timeout=min(0.2, remaining))
            except subprocess.TimeoutExpired:
                continue


def _drain_stdout(
    stream: TextIO,
    log_lines: list[str],
    on_line: LineCallback | None,
) -> None:
    try:
        for raw in iter(stream.readline, ""):
            line = raw.rstrip("\r\n")
            log_lines.append(line)
            if on_line is not None:
                on_line(line)
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
    except OSError:
        return
    try:
        proc.wait(timeout=3)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        proc.kill()
        proc.wait(timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        pass
