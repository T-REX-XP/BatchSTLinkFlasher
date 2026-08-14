"""Public flashing package exports (expanded as phases land)."""

from batch_stlink_flasher.flashing.job import FlashJob, FlashJobResult
from batch_stlink_flasher.flashing.models import (
    AdapterInfo,
    FlashConfig,
    JobState,
    OpenOcdPorts,
)
from batch_stlink_flasher.flashing.openocd import (
    build_openocd_command,
    build_program_command,
    default_bin_base_address,
    format_command_for_shell,
    summarize_openocd_error,
)
from batch_stlink_flasher.flashing.orchestrator import (
    AdapterJobResult,
    FlashOrchestrator,
    OrchestratorSummary,
)

__all__ = [
    "AdapterInfo",
    "AdapterJobResult",
    "FlashConfig",
    "FlashJob",
    "FlashJobResult",
    "FlashOrchestrator",
    "JobState",
    "OpenOcdPorts",
    "OrchestratorSummary",
    "build_openocd_command",
    "build_program_command",
    "default_bin_base_address",
    "format_command_for_shell",
    "summarize_openocd_error",
]
