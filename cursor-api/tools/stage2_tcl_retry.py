"""Strict, CI-only helper for one transient Tcl init retry."""

from __future__ import annotations

import os
import time
import tkinter as tk
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

_TCL_INIT_SIGNATURE = "Can't find a usable init.tcl"
_T = TypeVar("_T")


def ci_tcl_retry_enabled(environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return (
        str(env.get("GITHUB_ACTIONS", "")).strip().casefold() == "true"
        and bool(str(env.get("TCL_LIBRARY", "")).strip())
    )


def is_transient_tcl_init_error(exc: BaseException) -> bool:
    message = str(exc)
    return _TCL_INIT_SIGNATURE in message and "init.tcl" in message


def wait_for_tcl_init_readable() -> None:
    library = os.environ.get("TCL_LIBRARY", "").strip()
    if not library:
        return

    init_file = Path(library) / "init.tcl"
    for delay in (0.0, 0.05, 0.15):
        if delay:
            time.sleep(delay)
        try:
            init_file.read_bytes()
            return
        except OSError:
            continue

    # Nie maskuj problemu. Druga próba Tk zgłosi pełny TclError, ale krótki
    # read probe daje systemowi plików czas na zwolnienie przejściowej blokady.


def call_tk_init_with_transient_retry(
    original: Callable[..., _T],
    instance: object,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> _T:
    try:
        return original(instance, *args, **kwargs)
    except tk.TclError as exc:
        if not is_transient_tcl_init_error(exc):
            raise
        wait_for_tcl_init_readable()
        # Dokładnie jedna dodatkowa próba. Każdy kolejny błąd pozostaje
        # normalnym, blokującym failure testu.
        return original(instance, *args, **kwargs)


__all__ = [
    "call_tk_init_with_transient_retry",
    "ci_tcl_retry_enabled",
    "is_transient_tcl_init_error",
    "wait_for_tcl_init_readable",
]
