"""Desktop notifications (Windows toasts / cross-platform fallback).

Uzycie:
    from Komponenty._shared.notifications import notify
    notify("Ramka utwardzona", "ORD-0042 gotowa do zlozenia")

Implementacja:
- Windows: preferuje `winotify` (prawdziwe toasty Windows 10/11 z ikona + dzwiekiem),
  fallback do `ctypes.windll.user32.MessageBeep` + print w logu.
- macOS:   `osascript -e 'display notification ...'`
- Linux:   `notify-send` (libnotify).

Zadne z tych nie jest hard dependency - jesli biblioteki brak, funkcja
print-uje komunikat w konsoli i zwraca False. Wtedy aplikacja dalej dziala.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def notify(title: str, message: str, *, icon: str | None = None) -> bool:
    """Pokazuje systemowe powiadomienie. Zwraca True jesli udalo sie pokazac.

    Nie-blokujace - przy bledzie/braku bibliotek tylko drukuje do stdout.
    """
    try:
        if sys.platform.startswith("win"):
            return _notify_windows(title, message, icon=icon)
        if sys.platform == "darwin":
            return _notify_macos(title, message)
        return _notify_linux(title, message, icon=icon)
    except Exception as exc:  # noqa: BLE001
        print(f"[notify] {title}: {message}  (blad systemu notyfikacji: {exc})")
        return False


def _notify_windows(title: str, message: str, *, icon: str | None = None) -> bool:
    # Preferujemy winotify (pip install winotify) - prawdziwe toasty W10/11
    try:
        from winotify import Notification  # type: ignore[import-not-found]
    except ImportError:
        # Fallback: MessageBeep + print
        try:
            import ctypes
            ctypes.windll.user32.MessageBeep(0)  # type: ignore[attr-defined]
        except OSError:
            pass
        print(f"[notify] {title}: {message}")
        return False
    try:
        toast = Notification(
            app_id="GicleeApp",
            title=title,
            msg=message,
            icon=icon or "",
        )
        toast.show()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[notify] winotify failed: {exc}")
        print(f"[notify] {title}: {message}")
        return False


def _notify_macos(title: str, message: str) -> bool:
    # osascript jest zawsze dostepne na macOS
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}"'],
            check=False,
        )
        return True
    except OSError:
        print(f"[notify] {title}: {message}")
        return False


def _notify_linux(title: str, message: str, *, icon: str | None = None) -> bool:
    exe = shutil.which("notify-send")
    if not exe:
        print(f"[notify] {title}: {message}  (zainstaluj libnotify-bin)")
        return False
    args = [exe, title, message]
    if icon:
        args += ["-i", icon]
    try:
        subprocess.run(args, check=False)
        return True
    except OSError:
        print(f"[notify] {title}: {message}")
        return False
