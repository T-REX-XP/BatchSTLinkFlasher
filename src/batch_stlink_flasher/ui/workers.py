"""Background workers for discovery and flashing (keep UI thread free)."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from batch_stlink_flasher.flashing.job import FlashJobResult
from batch_stlink_flasher.flashing.models import AdapterInfo, FlashConfig
from batch_stlink_flasher.flashing.orchestrator import FlashOrchestrator, OrchestratorSummary
from batch_stlink_flasher.services.device_service import list_adapters


class DiscoveryWorker(QThread):
    """Enumerate ST-Links off the UI thread."""

    finished_ok = Signal(list)  # list[AdapterInfo]
    failed = Signal(str)

    def run(self) -> None:
        try:
            adapters = list_adapters()
            self.finished_ok.emit(adapters)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class FlashWorker(QThread):
    """Run FlashOrchestrator off the UI thread."""

    line_received = Signal(str, str)  # serial, line
    job_finished = Signal(str, str, str)  # serial, state value, error summary
    run_finished = Signal(object)  # OrchestratorSummary
    failed = Signal(str)

    def __init__(self, adapters: list[AdapterInfo], config: FlashConfig) -> None:
        super().__init__()
        self._adapters = adapters
        self._config = config
        self._orch: FlashOrchestrator | None = None

    def cancel(self) -> None:
        orch = self._orch
        if orch is not None:
            orch.cancel_all()

    def run(self) -> None:
        try:
            def on_line(adapter: AdapterInfo, line: str) -> None:
                self.line_received.emit(adapter.serial, line)

            def on_done(adapter: AdapterInfo, result: FlashJobResult) -> None:
                self.job_finished.emit(
                    adapter.serial,
                    result.state.value,
                    result.error_summary or "",
                )

            orch = FlashOrchestrator(
                self._adapters,
                self._config,
                on_line=on_line,
                on_job_done=on_done,
            )
            self._orch = orch
            summary: OrchestratorSummary = orch.run()
            self.run_finished.emit(summary)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
        finally:
            self._orch = None
