"""Subprocess bez widocznego okna konsoli na Windows."""

from __future__ import annotations

import subprocess
import sys


def no_console_kwargs() -> dict[str, int]:
    """Dodaj do subprocess.run / Popen, zeby nie migotalo okno cmd (ffmpeg itd.)."""
    if sys.platform != "win32":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return {"creationflags": flag} if flag else {}
