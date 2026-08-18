"""Smoke tests for Phase 5 UI (offscreen Qt)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialog, QLabel

from batch_stlink_flasher.flashing.models import AdapterInfo
from batch_stlink_flasher.services.settings import AppSettings, load_settings, save_settings
from batch_stlink_flasher import __version__
from batch_stlink_flasher.ui.about_dialog import AboutDialog
from batch_stlink_flasher.ui.config_panel import ConfigPanel
from batch_stlink_flasher.ui.device_table import DeviceTable
from batch_stlink_flasher.ui.main_window import MainWindow
from batch_stlink_flasher.ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_roundtrip(qapp: QApplication, tmp_path, monkeypatch) -> None:
    settings = AppSettings(
        openocd_path=str(tmp_path / "openocd.exe"),
        last_firmware_path=str(tmp_path / "a.elf"),
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f4x.cfg",
        scripts_search_path=str(tmp_path),
        bin_base_address="0x08000000",
        job_timeout_sec=90.0,
        flash_mode="sequential",
    )
    save_settings(settings)
    loaded = load_settings()
    assert loaded.target_cfg == "target/stm32f4x.cfg"
    assert loaded.job_timeout_sec == 90.0
    assert loaded.theme_mode in {"system", "light", "dark"}
    assert loaded.flash_mode == "sequential"


def test_normalize_flash_mode() -> None:
    from batch_stlink_flasher.services.settings import FlashMode, normalize_flash_mode

    assert normalize_flash_mode("auto") is FlashMode.AUTO
    assert normalize_flash_mode("SEQUENTIAL") is FlashMode.SEQUENTIAL
    assert normalize_flash_mode("seq") is FlashMode.SEQUENTIAL
    assert normalize_flash_mode(None) is FlashMode.AUTO
    assert normalize_flash_mode("nope") is FlashMode.AUTO

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
    assert table.item(0, 6).text() == "running"
    table.set_progress_for_serial("A", "programming (20%)")
    assert table.item(0, 7).text() == "programming (20%)"
    assert table.item(0, 3).text() == "-"
    table.setColumnHidden(1, False)
    table.setColumnWidth(1, 140)
    assert table.columnWidth(1) == 140
    table.apply_width_layout(500)
    assert table.isColumnHidden(4)
    table.apply_width_layout(1000)
    assert not table.isColumnHidden(4)
    table.apply_width_layout(500)
    table.apply_column_widths([32, 150, 110, 90, 70, 130, 90, 100, 200])
    table.apply_width_layout(1000)
    assert table.columnWidth(1) == 150


def test_config_panel_roundtrip(qapp: QApplication) -> None:
    panel = ConfigPanel()
    base = AppSettings(
        openocd_path="C:/tools/openocd.exe",
        last_firmware_path="fw.elf",
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
        job_timeout_sec=42,
        theme_mode="dark",
    )
    panel.apply_settings(base)
    settings = panel.merge_into(base)
    assert settings.last_firmware_path == "fw.elf"
    assert settings.target_cfg == "target/stm32f1x.cfg"
    assert settings.openocd_path == "C:/tools/openocd.exe"
    assert settings.job_timeout_sec == 42
    assert settings.theme_mode == "dark"


def test_settings_dialog_roundtrip(qapp: QApplication, tmp_path) -> None:
    base = AppSettings(
        openocd_path="openocd",
        last_firmware_path="keep.elf",
        interface_cfg="interface/stlink.cfg",
        target_cfg="target/stm32f1x.cfg",
        job_timeout_sec=120,
        theme_mode="system",
    )
    dialog = SettingsDialog(base)
    dialog.openocd_edit.setText(str(tmp_path / "openocd.exe"))
    dialog.scripts_edit.setText(str(tmp_path))
    dialog.timeout_edit.setText("not-a-number")
    dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("light"))
    dialog.flash_mode_combo.setCurrentIndex(dialog.flash_mode_combo.findData("sequential"))
    out = dialog.to_settings(base)
    assert out.last_firmware_path == "keep.elf"
    assert out.target_cfg == "target/stm32f1x.cfg"
    assert out.interface_cfg == "interface/stlink.cfg"
    assert out.job_timeout_sec == 120.0
    assert out.theme_mode == "light"
    assert out.flash_mode == "sequential"
    dialog.close()


def test_settings_dialog_browse(qapp: QApplication, monkeypatch, tmp_path) -> None:
    from batch_stlink_flasher.ui.file_filters import openocd_executable_filter

    openocd = tmp_path / "openocd.exe"
    openocd.write_text("", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    dialog = SettingsDialog(AppSettings())

    def fake_open(*a, **k):
        caption = a[1] if len(a) > 1 else ""
        filt = a[3] if len(a) > 3 else k.get("filter", "")
        if "executable" in caption.lower():
            assert filt == openocd_executable_filter()
            return (str(openocd), "")
        return (str(openocd), "")

    monkeypatch.setattr(
        "batch_stlink_flasher.ui.settings_dialog.QFileDialog.getOpenFileName",
        fake_open,
    )
    dialog._browse_openocd()  # noqa: SLF001
    assert dialog.openocd_edit.text() == str(openocd)
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.settings_dialog.QFileDialog.getExistingDirectory",
        lambda *a, **k: str(scripts),
    )
    dialog._browse_scripts()  # noqa: SLF001
    assert dialog.scripts_edit.text() == str(scripts)
    dialog.close()


def test_config_panel_browse_filters(qapp: QApplication, monkeypatch, tmp_path) -> None:
    from batch_stlink_flasher.ui.file_filters import FIRMWARE_FILTER

    panel = ConfigPanel()
    fw = tmp_path / "a.elf"
    fw.write_text("", encoding="utf-8")

    def fake_open(*a, **k):
        filt = a[3] if len(a) > 3 else k.get("filter", "")
        caption = a[1] if len(a) > 1 else ""
        if "firmware" in caption.lower():
            assert filt == FIRMWARE_FILTER
            assert "*.elf" in filt and "*.hex" in filt and "*.bin" in filt
            return (str(fw), "")
        return (str(fw), "")

    monkeypatch.setattr(
        "batch_stlink_flasher.ui.config_panel.QFileDialog.getOpenFileName",
        fake_open,
    )
    panel._browse_firmware()  # noqa: SLF001
    assert panel.firmware_edit.text() == str(fw)


def test_file_filters_module(monkeypatch) -> None:
    from batch_stlink_flasher.ui import file_filters as ff

    assert "*.elf" in ff.FIRMWARE_FILTER
    assert "*.cfg" in ff.OPENOCD_CFG_FILTER
    assert "*.json" in ff.LOG_EXPORT_FILTER
    exe = ff.openocd_executable_filter()
    assert "All files" in exe
    assert "openocd" in exe.lower()
    monkeypatch.setattr(ff.sys, "platform", "linux")
    posix = ff.openocd_executable_filter()
    assert "openocd" in posix
    assert "*.exe" not in posix


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
    assert window.main_splitter.count() == 2
    assert "OpenOCD:" in window.tools_summary.text()
    window.set_theme_mode("light")
    assert window._current_settings().theme_mode == "light"  # noqa: SLF001
    window.set_theme_mode("system")
    err = window._validate(window._current_settings())  # noqa: SLF001
    assert err is not None
    window._reset_layout()  # noqa: SLF001
    window._save_ui_state()  # noqa: SLF001
    window._restore_ui_state()  # noqa: SLF001
    window._update_summary_idle()  # noqa: SLF001
    window._update_summary_counts(succeeded=1, failed=0, cancelled=0, running=0)  # noqa: SLF001
    assert "Succeeded: 1" in window.summary_label.text()
    window.close()


def test_main_window_open_settings(qapp: QApplication, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.DiscoveryWorker.start",
        lambda self: None,
    )
    window = MainWindow(auto_refresh=False)

    class FakeDialog(SettingsDialog):
        def __init__(self, settings, parent=None):
            super().__init__(settings, parent)
            self.openocd_edit.setText(str(tmp_path / "ocd.exe"))
            self.timeout_edit.setText("77")
            self.theme_combo.setCurrentIndex(self.theme_combo.findData("dark"))

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("batch_stlink_flasher.ui.main_window.SettingsDialog", FakeDialog)
    window.open_settings()
    assert window._settings.job_timeout_sec == 77.0  # noqa: SLF001
    assert window._settings.theme_mode == "dark"  # noqa: SLF001
    assert str(tmp_path / "ocd.exe") in window.tools_summary.text()
    window.close()


def test_main_window_accepts_initial_adapters(qapp: QApplication, monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.main_window.DiscoveryWorker.start",
        lambda self: None,
    )
    adapters = [
        AdapterInfo(
            serial="AABB",
            hla_serial='"\\xaa\\xbb"',
            vid=0x0483,
            pid=0x3748,
            product="ST-Link",
            multi_adapter_ok=True,
            usb_port=1,
            usb_hub=2,
        )
    ]
    window = MainWindow(initial_adapters=adapters, auto_refresh=False)
    assert len(window.device_table.adapters()) == 1
    assert window.device_table.item(0, 3).text() == "1 (hub 2)"
    window.close()


def test_config_panel_browse_firmware(qapp: QApplication, monkeypatch, tmp_path) -> None:
    panel = ConfigPanel()
    fw = tmp_path / "a.elf"
    fw.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.config_panel.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(fw), ""),
    )
    panel._browse_firmware()  # noqa: SLF001
    assert panel.firmware_edit.text() == str(fw)


def test_config_scanner(tmp_path) -> None:
    from batch_stlink_flasher.ui.config_scanner import (
        get_default_interface_config,
        get_default_target_config,
        scan_scripts_directory,
    )

    # Test with None/empty path
    interfaces, targets = scan_scripts_directory(None)
    assert interfaces == []
    assert targets == []

    interfaces, targets = scan_scripts_directory("")
    assert interfaces == []
    assert targets == []

    # Test with non-existent path
    interfaces, targets = scan_scripts_directory(str(tmp_path / "nonexistent"))
    assert interfaces == []
    assert targets == []

    # Test with empty scripts directory
    interfaces, targets = scan_scripts_directory(str(tmp_path))
    assert interfaces == []
    assert targets == []

    # Test with interface configs
    iface_dir = tmp_path / "interface"
    iface_dir.mkdir()
    (iface_dir / "stlink.cfg").write_text("", encoding="utf-8")
    (iface_dir / "stlink-v2.cfg").write_text("", encoding="utf-8")
    (iface_dir / "subdir").mkdir()
    (iface_dir / "subdir" / "nested.cfg").write_text("", encoding="utf-8")

    interfaces, targets = scan_scripts_directory(str(tmp_path))
    assert len(interfaces) == 3
    assert "interface/stlink.cfg" in interfaces
    assert "interface/stlink-v2.cfg" in interfaces
    assert "interface/subdir/nested.cfg" in interfaces
    assert targets == []

    # Test with target configs
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    (target_dir / "stm32f1x.cfg").write_text("", encoding="utf-8")
    (target_dir / "stm32f4x.cfg").write_text("", encoding="utf-8")

    interfaces, targets = scan_scripts_directory(str(tmp_path))
    assert len(interfaces) == 3
    assert len(targets) == 2
    assert "target/stm32f1x.cfg" in targets
    assert "target/stm32f4x.cfg" in targets

    # Test default values
    assert get_default_interface_config() == "interface/stlink.cfg"
    assert get_default_target_config() == "target/stm32f1x.cfg"


def test_config_panel_dropdown_refresh(qapp: QApplication, tmp_path) -> None:
    """Test that config panel target combo refreshes with options."""
    from batch_stlink_flasher.ui.config_scanner import get_default_target_config

    panel = ConfigPanel()

    # Create scripts directory with target configs
    scripts_dir = tmp_path / "scripts"
    target_dir = scripts_dir / "target"
    target_dir.mkdir(parents=True)
    (target_dir / "stm32f1x.cfg").write_text("", encoding="utf-8")
    (target_dir / "stm32f4x.cfg").write_text("", encoding="utf-8")

    # Apply settings with scripts path
    settings = AppSettings(
        target_cfg="target/stm32f1x.cfg",
        scripts_search_path=str(scripts_dir),
    )
    panel.apply_settings(settings)

    # Verify combo has scanned targets (2) plus well-known defaults
    assert panel.target_combo.count() >= 2
    assert panel.target_combo.currentText() == "target/stm32f1x.cfg"

    # Test with custom value not in list
    settings2 = AppSettings(
        target_cfg="target/custom.cfg",
        scripts_search_path=str(scripts_dir),
    )
    panel.apply_settings(settings2)
    assert panel.target_combo.currentText() == "target/custom.cfg"

    # Test with empty scripts path — well-known defaults are still shown
    settings3 = AppSettings(
        target_cfg="target/stm32f1x.cfg",
        scripts_search_path="",
    )
    panel.apply_settings(settings3)
    assert panel.target_combo.count() >= 1  # well-known defaults always present
    assert panel.target_combo.currentText() == "target/stm32f1x.cfg"


def test_about_dialog(qapp: QApplication) -> None:
    dialog = AboutDialog()
    assert "About" in dialog.windowTitle()
    version_label = dialog.findChild(QLabel, "aboutVersion")
    assert version_label is not None
    text = version_label.text()
    assert "Version" in text
    assert str(__version__.split(".")[-1]) in text or "build" in text.lower()
    dialog.close()
