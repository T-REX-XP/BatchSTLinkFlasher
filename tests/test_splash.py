"""Splash screen smoke tests."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QLabel

from batch_stlink_flasher.ui.splash_screen import SplashScreen


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_splash_builds_with_art(qapp: QApplication, monkeypatch) -> None:
    monkeypatch.setattr(
        "batch_stlink_flasher.ui.splash_screen.DiscoveryWorker.start",
        lambda self: None,
    )
    splash = SplashScreen()
    art = splash.findChild(QLabel, "splashArt")
    assert art is not None
    assert not art.pixmap().isNull()
    splash.center_on_screen()
    splash.start_scan()
    splash.close()


def test_splash_scan_results(qapp: QApplication, monkeypatch) -> None:
    from batch_stlink_flasher.flashing.models import AdapterInfo

    monkeypatch.setattr(
        "batch_stlink_flasher.ui.splash_screen.DiscoveryWorker.start",
        lambda self: None,
    )
    splash = SplashScreen()
    seen: list[tuple[list, str]] = []
    splash.scan_finished.connect(lambda a, e: seen.append((a, e)))

    splash._on_ok([])  # noqa: SLF001
    assert "No ST-Link" in splash.status_label.text()
    splash._on_ok(  # noqa: SLF001
        [
            AdapterInfo(
                serial="A",
                hla_serial='"\\xaa"',
                vid=0x0483,
                pid=0x3748,
                product="ST",
                multi_adapter_ok=True,
            )
        ]
    )
    assert "Found 1" in splash.status_label.text()
    splash._on_ok(  # noqa: SLF001
        [
            AdapterInfo(
                serial="A",
                hla_serial='"\\xaa"',
                vid=0x0483,
                pid=0x3748,
                product="ST",
                multi_adapter_ok=True,
            ),
            AdapterInfo(
                serial="B",
                hla_serial='"\\xbb"',
                vid=0x0483,
                pid=0x3748,
                product="ST",
                multi_adapter_ok=True,
            ),
        ]
    )
    assert "Found 2" in splash.status_label.text()
    splash._on_failed("boom")  # noqa: SLF001
    assert "boom" in splash.status_label.text()
    assert seen[-1][1] == "boom"
    splash.close()
