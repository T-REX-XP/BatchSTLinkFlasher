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

__all__ = [
    "AdapterInfo",
    "FlashConfig",
    "FlashJob",
    "FlashJobResult",
    "JobState",
    "OpenOcdPorts",
    "build_openocd_command",
    "build_program_command",
    "default_bin_base_address",
    "format_command_for_shell",
    "summarize_openocd_error",
]
