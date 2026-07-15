"""Neutralny pomocnik do wywoływania funkcji build_view komponentów (inline)."""

from __future__ import annotations

import inspect
import tkinter as tk
from collections.abc import Callable
from typing import Any


def supports_on_open_component(
    builder: Callable[..., Any],
) -> bool:
    """Sprawdza za pomocą inspect.signature, czy builder obsługuje on_open_component."""
    try:
        signature = inspect.signature(builder)
    except (TypeError, ValueError):
        return False

    parameter = signature.parameters.get("on_open_component")
    if parameter is not None and parameter.kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        return True

    return any(
        item.kind is inspect.Parameter.VAR_KEYWORD
        for item in signature.parameters.values()
    )


def invoke_inline_builder(
    builder: Callable[..., Any],
    parent: tk.Widget,
    on_back: Callable[[], None],
    *,
    on_open_component: Callable[[str], None] | None = None,
) -> Any:
    """Bezpiecznie wywołuje builder dokładnie raz.

    Jeżeli builder akceptuje on_open_component (lub kwargs), przekazuje go.
    Wszystkie TypeError i inne wyjątki z wewnątrz buildera są propagowane do callera.
    """
    if supports_on_open_component(builder):
        return builder(parent, on_back, on_open_component=on_open_component)
    return builder(parent, on_back)


__all__ = [
    "supports_on_open_component",
    "invoke_inline_builder",
]
