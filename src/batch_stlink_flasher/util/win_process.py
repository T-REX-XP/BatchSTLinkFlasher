"""Windows subprocess helpers (hide console windows from GUI apps)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def hidden_subprocess_kwargs() -> dict[str, Any]:
    """
    Extra kwargs for ``subprocess.run`` / ``Popen`` on Windows GUI apps.

    Hides consoles for leftover tools such as ``st-info`` / OpenOCD. Device PnP
    discovery itself must **not** spawn PowerShell (see ``windows_pnp.py``).
    """
    if sys.platform != "win32":
        return {}

    kwargs: dict[str, Any] = {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if flag:
        kwargs["creationflags"] = flag

    # Belt-and-suspenders: some hosts still flash briefly without SW_HIDE.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    kwargs["startupinfo"] = startupinfo
    return kwargs
