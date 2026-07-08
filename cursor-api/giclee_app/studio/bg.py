"""Worker w tle dla Studio — długie IO poza mainloop, wynik wraca na wątku UI.

Wzorzec: `run_async(widget, func, on_done)` uruchamia `func()` w wątku daemon,
a wynik dostarcza przez polling `widget.after()` — bez wołania tkinter
z obcego wątku (thread-safe).
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from typing import Any

_DEFAULT_POLL_MS = 40


def run_async(
    widget: tk.Misc,
    func: Callable[[], Any],
    on_done: Callable[[Any], None],
    *,
    on_error: Callable[[BaseException], None] | None = None,
    poll_ms: int = _DEFAULT_POLL_MS,
) -> None:
    """Wykonuje `func()` w wątku; `on_done(result)` woła na wątku UI.

    Jeśli widget zostanie zniszczony przed końcem pracy, wynik jest porzucany.
    Błędy z `func` trafiają do `on_error` (jeśli podano), inaczej są ignorowane.
    """
    box: dict[str, Any] = {}

    def _worker() -> None:
        try:
            box["result"] = func()
        except BaseException as exc:  # noqa: BLE001 — soft-fail, raport do on_error
            box["error"] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    def _poll() -> None:
        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        if thread.is_alive():
            try:
                widget.after(poll_ms, _poll)
            except tk.TclError:
                pass
            return
        if "error" in box:
            if on_error is not None:
                on_error(box["error"])
            return
        on_done(box.get("result"))

    try:
        widget.after(poll_ms, _poll)
    except tk.TclError:
        pass
