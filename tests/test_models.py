"""Unit tests for FlashConfig / AdapterInfo / JobState / OpenOcdPorts."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_stlink_flasher.flashing.models import (
    AdapterInfo,
    FlashConfig,
    JobState,
    OpenOcdPorts,
)


def test_adapter_info_frozen() -> None:
    adapter = AdapterInfo(
        serial="ABC",
        hla_serial="ABC",
        vid=0x0483,
        pid=0x3748,
        product="ST-Link",
    )
    with pytest.raises(Exception):
        adapter.serial = "other"  # type: ignore[misc]


def test_job_state_values() -> None:
    assert JobState.RUNNING.value == "running"
    assert {s.value for s in JobState} == {
        "idle",
        "queued",
        "running",
        "succeeded",
        "failed",
        "cancelled",
    }


def test_openocd_ports_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="distinct"):
        OpenOcdPorts(gdb=3333, telnet=3333, tcl=6666)


def test_openocd_ports_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="TCP port"):
        OpenOcdPorts(gdb=0, telnet=4444, tcl=6666)


def test_flash_config_bin_requires_address(tmp_path: Path) -> None:
    cfg = FlashConfig(
        openocd_path=Path("openocd"),
        firmware_path=tmp_path / "app.bin",
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
        bin_base_address=None,
    )
    with pytest.raises(ValueError, match="bin_base_address"):
        cfg.validate()


def test_flash_config_elf_ok_without_address(tmp_path: Path) -> None:
    cfg = FlashConfig(
        openocd_path=Path("openocd"),
        firmware_path=tmp_path / "app.elf",
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )
    cfg.validate()
    assert cfg.firmware_kind() == "elf"


def test_flash_config_rejects_unknown_suffix(tmp_path: Path) -> None:
    cfg = FlashConfig(
        openocd_path=Path("openocd"),
        firmware_path=tmp_path / "app.srec",
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
    )
    with pytest.raises(ValueError, match="Unsupported firmware"):
        cfg.validate()
