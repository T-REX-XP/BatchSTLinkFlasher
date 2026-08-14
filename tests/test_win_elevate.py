"""Coverage for Windows UAC elevation helpers and asset path fallbacks."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from batch_stlink_flasher.assets_util import asset_path
from batch_stlink_flasher.util import win_elevate


def test_is_user_an_admin_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "win32")
    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "IsUserAnAdmin",
        lambda: 1,
        raising=False,
    )
    assert win_elevate.is_user_an_admin() is True


def test_is_user_an_admin_false_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "linux")
    assert win_elevate.is_user_an_admin() is False

    monkeypatch.setattr(win_elevate.sys, "platform", "win32")

    def _boom() -> bool:
        raise OSError("no shell32")

    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "IsUserAnAdmin",
        _boom,
        raising=False,
    )
    assert win_elevate.is_user_an_admin() is False


def test_run_elevated_rejects_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "linux")
    with pytest.raises(OSError, match="Windows"):
        win_elevate.run_elevated("helper.exe", "--ping")


def test_run_elevated_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "win32")
    exe = tmp_path / "helper.exe"
    exe.write_bytes(b"x")

    def shell_execute_ex(info_ref) -> int:
        info = info_ref._obj  # ctypes byref
        info.hProcess = 0xABC
        return 1

    class _Kernel:
        @staticmethod
        def WaitForSingleObject(_handle, _ms) -> int:
            return win_elevate.WAIT_OBJECT_0

        @staticmethod
        def GetExitCodeProcess(_handle, code_ref) -> int:
            code_ref._obj.value = 42
            return 1

        @staticmethod
        def CloseHandle(_handle) -> int:
            return 1

    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "ShellExecuteExW",
        shell_execute_ex,
        raising=False,
    )
    monkeypatch.setattr(win_elevate.ctypes, "get_last_error", lambda: 0)
    monkeypatch.setattr(win_elevate.ctypes.windll, "kernel32", _Kernel(), raising=False)

    assert win_elevate.run_elevated(exe, "--ok", cwd=tmp_path) == 42


def test_run_elevated_shell_execute_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "win32")
    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "ShellExecuteExW",
        lambda _info: 0,
        raising=False,
    )
    monkeypatch.setattr(win_elevate.ctypes, "get_last_error", lambda: 1223)
    with pytest.raises(OSError, match="ShellExecuteExW"):
        win_elevate.run_elevated("x.exe", "")


def test_run_elevated_no_process_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "win32")

    def shell_execute_ex(info_ref) -> int:
        info_ref._obj.hProcess = None
        return 1

    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "ShellExecuteExW",
        shell_execute_ex,
        raising=False,
    )
    with pytest.raises(OSError, match="no process handle"):
        win_elevate.run_elevated("x.exe", "")


def test_run_elevated_wait_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "win32")
    closed: list[int] = []

    def shell_execute_ex(info_ref) -> int:
        info_ref._obj.hProcess = 99
        return 1

    class _Kernel:
        @staticmethod
        def WaitForSingleObject(_handle, _ms) -> int:
            return 0x102  # WAIT_TIMEOUT-ish

        @staticmethod
        def CloseHandle(handle) -> int:
            closed.append(handle)
            return 1

    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "ShellExecuteExW",
        shell_execute_ex,
        raising=False,
    )
    monkeypatch.setattr(win_elevate.ctypes.windll, "kernel32", _Kernel(), raising=False)
    with pytest.raises(OSError, match="WaitForSingleObject"):
        win_elevate.run_elevated("x.exe", "")
    assert closed == [99]


def test_run_elevated_get_exit_code_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(win_elevate.sys, "platform", "win32")
    closed: list[int] = []

    def shell_execute_ex(info_ref) -> int:
        info_ref._obj.hProcess = 77
        return 1

    class _Kernel:
        @staticmethod
        def WaitForSingleObject(_handle, _ms) -> int:
            return win_elevate.WAIT_OBJECT_0

        @staticmethod
        def GetExitCodeProcess(_handle, _code_ref) -> int:
            return 0

        @staticmethod
        def CloseHandle(handle) -> int:
            closed.append(handle)
            return 1

    monkeypatch.setattr(
        win_elevate.ctypes.windll.shell32,
        "ShellExecuteExW",
        shell_execute_ex,
        raising=False,
    )
    monkeypatch.setattr(win_elevate.ctypes.windll, "kernel32", _Kernel(), raising=False)
    with pytest.raises(OSError, match="GetExitCodeProcess"):
        win_elevate.run_elevated("x.exe", "")
    assert closed == [77]


def test_asset_path_meipass_flat_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import batch_stlink_flasher.assets_util as assets_util

    flat = tmp_path / "assets"
    flat.mkdir()
    target = flat / "logo.png"
    target.write_bytes(b"png")
    monkeypatch.setattr(assets_util.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert assets_util.asset_path("logo.png") == target


def test_asset_path_missing_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import batch_stlink_flasher.assets_util as assets_util

    monkeypatch.setattr(assets_util.sys, "_MEIPASS", str(tmp_path), raising=False)
    # Force package resources path to miss as well by requesting a nonsense name.
    assert asset_path("definitely-missing-asset-xyz.dat") is None


def test_asset_path_resources_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import batch_stlink_flasher.assets_util as assets_util
    from importlib import resources as res

    monkeypatch.delattr(assets_util.sys, "_MEIPASS", raising=False)

    def _boom(*_a, **_k):
        raise FileNotFoundError("no package")

    monkeypatch.setattr(res, "files", _boom)
    # Fallback to source tree assets still works for real files.
    path = assets_util.asset_path("app_icon.png")
    assert path is not None and path.is_file()
