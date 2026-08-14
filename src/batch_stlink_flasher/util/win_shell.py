"""Windows shell identity helpers (taskbar / Alt+Tab branding)."""

from __future__ import annotations

import sys


# Stable ID so Windows does not group this app under python.exe when run from source.
APP_USER_MODEL_ID = "BatchSTLinkFlasher.App"


def set_app_user_model_id(app_id: str = APP_USER_MODEL_ID) -> bool:
    """
    Tell Windows this process is our app (not the Python host).

    Must run before any windows are created. Without this, taskbar / Alt+Tab
    keep showing the python.exe icon even when ``QApplication.setWindowIcon``
    is set. No-op on non-Windows or if the call fails.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return int(result) == 0
    except (AttributeError, OSError, ValueError):
        return False
