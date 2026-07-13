"""CI-only Tcl/Tk validation helpers.

Stage 2 uses the Tcl/Tk runtime installed by actions/setup-python directly.
A failed ``_tkinter.create(...)`` can leave the target Tk object partially
initialized, so this module deliberately never retries ``Tk.__init__`` on the
same object. The legacy function names remain only as compatibility shims for
the existing test bootstrap.
"""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar

_RUNTIME_SIGNATURES = (
    "Can't find a usable init.tcl",
    "Can't find a usable tk.tcl",
)
_T = TypeVar("_T")


def ci_tcl_retry_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return ``False``: retrying a partially initialized Tk object is unsafe."""

    _ = environ
    return False


def is_transient_tcl_runtime_error(exc: BaseException) -> bool:
    """Classify the historical Stage 2 runtime signatures for diagnostics only."""

    message = str(exc)
    return any(signature in message for signature in _RUNTIME_SIGNATURES)


def is_transient_tcl_init_error(exc: BaseException) -> bool:
    """Backward-compatible alias for the original narrow helper name."""

    return is_transient_tcl_runtime_error(exc)


def wait_for_tcl_runtime_readable(
    tcl_library: str | None = None,
    tk_library: str | None = None,
) -> bool:
    """Validate the configured runtime once without sleeping or retrying Tk."""

    configured_tcl = (tcl_library or os.environ.get("TCL_LIBRARY", "")).strip()
    configured_tk = (tk_library or os.environ.get("TK_LIBRARY", "")).strip()
    if not configured_tcl or not configured_tk:
        return False

    required = (
        Path(configured_tcl) / "init.tcl",
        Path(configured_tk) / "tk.tcl",
        Path(configured_tk) / "spinbox.tcl",
        Path(configured_tk) / "ttk" / "defaults.tcl",
        Path(configured_tk) / "ttk" / "winTheme.tcl",
    )
    try:
        for path in required:
            path.read_bytes()
    except OSError:
        return False
    return True


def wait_for_tcl_init_readable(library: str | None = None) -> bool:
    """Backward-compatible validation wrapper; it does not wait or retry."""

    return wait_for_tcl_runtime_readable(tcl_library=library)


def call_tk_init_with_transient_retry(
    original: Callable[..., _T],
    instance: object,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> _T:
    """Delegate exactly once; never reinitialize the same Tk object."""

    return original(instance, *args, **kwargs)


__all__ = [
    "call_tk_init_with_transient_retry",
    "ci_tcl_retry_enabled",
    "is_transient_tcl_init_error",
    "is_transient_tcl_runtime_error",
    "wait_for_tcl_init_readable",
    "wait_for_tcl_runtime_readable",
]
