"""Elevate a short helper process with UAC (Windows)."""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from pathlib import Path

logger = logging.getLogger(__name__)

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_HIDE = 0
WAIT_OBJECT_0 = 0
INFINITE = 0xFFFFFFFF


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def is_user_an_admin() -> bool:
    """True when the current process token is elevated."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def run_elevated(exe: str | Path, parameters: str, *, cwd: str | Path | None = None) -> int:
    """
    Launch ``exe`` with UAC (``runas``) and wait for exit.

    Returns the child process exit code. Raises ``OSError`` if ShellExecuteEx fails
    (including user canceling the UAC dialog).
    """
    if sys.platform != "win32":
        raise OSError("elevation is only supported on Windows")

    info = _SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(_SHELLEXECUTEINFOW)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.hwnd = None
    info.lpVerb = "runas"
    info.lpFile = str(exe)
    info.lpParameters = parameters
    info.lpDirectory = str(cwd) if cwd is not None else None
    info.nShow = SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        err = ctypes.get_last_error()
        raise OSError(err, f"ShellExecuteExW(runas) failed (WinError {err})")

    if not info.hProcess:
        raise OSError("ShellExecuteExW returned no process handle")

    kernel32 = ctypes.windll.kernel32
    wait = kernel32.WaitForSingleObject(info.hProcess, INFINITE)
    if wait != WAIT_OBJECT_0:
        kernel32.CloseHandle(info.hProcess)
        raise OSError(f"WaitForSingleObject failed: {wait}")

    code = wintypes.DWORD()
    if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code)):
        kernel32.CloseHandle(info.hProcess)
        raise OSError("GetExitCodeProcess failed")
    kernel32.CloseHandle(info.hProcess)
    return int(code.value)
