"""Windows subprocess helpers (hide console windows from GUI apps)."""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def hidden_subprocess_kwargs() -> dict[str, Any]:
    """
    Extra kwargs for ``subprocess.run`` / ``Popen`` on Windows GUI apps.

    Without ``CREATE_NO_WINDOW``, launching ``powershell.exe`` / console tools
    briefly flashes a black console behind the Qt window.
    """
    if sys.platform != "win32":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if not flag:
        return {}
    return {"creationflags": flag}
