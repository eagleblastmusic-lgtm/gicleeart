"""Strict, CI-only recovery for transient Tcl runtime read failures."""

from __future__ import annotations

import os
import time
import tkinter as tk
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

_TCL_INIT_SIGNATURE = "Can't find a usable init.tcl"
_SOURCE_TCL_ENV = "GICLEEAPP_TCL_SOURCE_LIBRARY"
_SOURCE_TK_ENV = "GICLEEAPP_TK_SOURCE_LIBRARY"
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


def wait_for_tcl_init_readable(library: str | None = None) -> bool:
    configured = (library or os.environ.get("TCL_LIBRARY", "")).strip()
    if not configured:
        return False

    init_file = Path(configured) / "init.tcl"
    for delay in (0.0, 0.05, 0.15, 0.35):
        if delay:
            time.sleep(delay)
        try:
            init_file.read_bytes()
            return True
        except OSError:
            continue
    return False


def activate_preflighted_source_runtime(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Switch this process to the immutable setup-python Tcl/Tk runtime."""

    env = environ if environ is not None else os.environ
    source_tcl = str(env.get(_SOURCE_TCL_ENV, "")).strip()
    source_tk = str(env.get(_SOURCE_TK_ENV, "")).strip()
    if not source_tcl or not source_tk:
        return False

    required = (
        Path(source_tcl) / "init.tcl",
        Path(source_tk) / "tk.tcl",
        Path(source_tk) / "spinbox.tcl",
        Path(source_tk) / "ttk" / "defaults.tcl",
    )
    try:
        for path in required:
            path.read_bytes()
    except OSError:
        return False

    os.environ["TCL_LIBRARY"] = source_tcl
    os.environ["TK_LIBRARY"] = source_tk
    return True


def call_tk_init_with_transient_retry(
    original: Callable[..., _T],
    instance: object,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> _T:
    try:
        return original(instance, *args, **kwargs)
    except tk.TclError as first_exc:
        if not is_transient_tcl_init_error(first_exc):
            raise

    wait_for_tcl_init_readable()
    try:
        return original(instance, *args, **kwargs)
    except tk.TclError as second_exc:
        if not is_transient_tcl_init_error(second_exc):
            raise
        if not activate_preflighted_source_runtime():
            raise

    wait_for_tcl_init_readable()
    return original(instance, *args, **kwargs)


__all__ = [
    "activate_preflighted_source_runtime",
    "call_tk_init_with_transient_retry",
    "ci_tcl_retry_enabled",
    "is_transient_tcl_init_error",
    "wait_for_tcl_init_readable",
]
