"""Windows clipboard helper for Performance Agent (PA-1F)."""

from __future__ import annotations

import subprocess
import sys


class ClipboardCopyError(RuntimeError):
    """Raised when copying text to the system clipboard fails."""


def describe_clipboard_support() -> str:
    """Return a human-readable description of clipboard support on this platform."""
    if sys.platform == "win32":
        return "Windows PowerShell Set-Clipboard"
    return "no"


def copy_text_to_clipboard(text: str) -> None:
    """Copy *text* to the Windows clipboard via PowerShell ``Set-Clipboard``."""
    if sys.platform != "win32":
        raise ClipboardCopyError("Clipboard copy is only supported on Windows.")

    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Set-Clipboard -Value ([Console]::In.ReadToEnd())",
            ],
            input=text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClipboardCopyError("Clipboard copy timed out after 5 seconds.") from exc
    except (OSError, FileNotFoundError) as exc:
        raise ClipboardCopyError(f"Clipboard copy failed: {exc}") from exc

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        detail = err or f"exit code {proc.returncode}"
        raise ClipboardCopyError(f"Clipboard copy failed: {detail}")
