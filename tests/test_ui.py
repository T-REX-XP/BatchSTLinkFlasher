"""Smoke tests for Phase 5 UI (offscreen Qt)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.services.settings import AppSettings, load_settings, save_settings
from batch_stlink_flasher import __version__
from batch_stlink_flasher.ui.about_dialog import AboutDialog
from batch_stlink_flasher.ui.config_panel import ConfigPanel
from batch_stlink_flasher.ui.device_table import DeviceTable
from batch_stlink_flasher.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_roundtrip(qapp: QApplication, tmp_path, monkeypatch) -> None:
    # Isolate QSettings to a temp org by writing then reading known values.
    settings = AppSettings(
        openocd_path=str(tmp_path / "openocd.exe"),
        last_firmware_path=str(tmp_path / "a.elf"),
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f4x.cfg",
        scripts_search_path=str(tmp_path),
        bin_base_address="0x08000000",
        job_timeout_sec=90.0,
    )
    save_settings(settings)
    loaded = load_settings()
    assert loaded.target_cfg == "target/stm32f4x.cfg"
    assert loaded.job_timeout_sec == 90.0
    assert loaded.theme_mode in {"system", "light", "dark"}


def test_device_table_selection(qapp: QApplication) -> None:
    table = DeviceTable()
    adapters = [
        AdapterInfo(
            serial="A",
            hla_serial='"\\xaa"',
            vid=0x0483,
            pid=0x3748,
            product="ST-Link",
            multi_adapter_ok=True,
        ),
        AdapterInfo(
            serial="%",
            hla_serial="",
            vid=0x0483,
            pid=0x3748,
            product="Clone",
            multi_adapter_ok=False,
            skip_reason="placeholder",
        ),
    ]
    table.set_adapters(adapters)
    assert len(table.selected_adapters()) == 2
    table.set_all_checked(False)
    assert table.selected_adapters() == []
    table.set_all_checked(True)
    assert len(table.selected_adapters()) == 2
    table.set_status_for_serial("A", "running")
    assert table.item(0, 5).text() == "running"
    table.set_progress_for_serial("A", "programming (20%)")
    assert table.item(0, 6).text() == "programming (20%)"


def test_config_panel_roundtrip(qapp: QApplication) -> None:
    panel = ConfigPanel()
    panel.apply_settings(
        AppSettings(
            openocd_path="openocd",
            last_firmware_path="fw.elf",
            interface_cfg="interface/stlink.cfg",
            target_cfg="target/stm32f1x.cfg",
            job_timeout_sec=42,
        )
    )
    settings = panel.to_settings()
    assert settings.last_firmware_path == "fw.elf"
    assert settings.job_timeout_sec == 42


def test_main_window_builds(qapp: QApplication, monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.DiscoveryWorker.start",
        lambda self: None,
    )
    window = MainWindow(auto_refresh=False)
    assert window.windowTitle().startswith("Batch ST-Link Flasher")
    assert window.flash_btn.text() == "Flash"
    assert window.flash_btn.objectName() == "primaryButton"
    assert not window.flash_btn.icon().isNull()
    assert window._theme_actions  # noqa: SLF001
    window.set_theme_mode("light")
    assert window.config_panel.to_settings().theme_mode == "light"
    window.set_theme_mode("system")
    # Validation with empty selection / missing files
    err = window._validate(window.config_panel.to_settings())  # noqa: SLF001
    assert err is not None
    window.close()


def test_about_dialog(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QLabel

    dialog = AboutDialog()
    assert "About" in dialog.windowTitle()
    version_label = dialog.findChild(QLabel, "aboutVersion")
    assert version_label is not None
    text = version_label.text()
    assert "Version" in text
    assert str(__version__.split(".")[-1]) in text or "build" in text.lower()
    dialog.close()
