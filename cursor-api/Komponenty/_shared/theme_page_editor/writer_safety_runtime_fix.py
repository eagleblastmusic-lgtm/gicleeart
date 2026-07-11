"""WS-1.1: opóźnione rozwiązywanie kontekstu przycisków wspólnego edytora.

``gui_shell`` tworzy przyciski zanim lokalne funkcje ``_save_all`` i ``_deploy``
zostaną przypisane do komórek domknięcia. Kontekst musi więc być odczytywany
dopiero po zakończeniu budowy UI, a nie w chwili konstruowania ``ttk.Button``.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

from . import writer_safety as ws


def _resolve_context(
    command: Callable[..., Any] | None,
    target_name: str,
    host: tk.Misc,
    config: Any,
):
    return ws._context_from_command(command, target_name, host, config)


def _button_with_deferred_context(
    self: Any,
    master: tk.Misc | None = None,
    *args: Any,
    **kwargs: Any,
):
    text = str(kwargs.get("text") or "")
    command = kwargs.get("command")
    build = ws._BUILD_STACK[-1] if ws._BUILD_STACK else None

    if build is not None and callable(command) and text == "Zapisz":
        host, config = build
        original_command = command
        kwargs["text"] = "Zapisz wersję"
        kwargs["command"] = lambda: ws._run_variant_only_save(
            _resolve_context(original_command, "_save_all", host, config)
        )
        widget = self._ttk.Button(master, *args, **kwargs)

        if master is not None:
            ttk_module = self._ttk

            def add_apply_button() -> None:
                context = _resolve_context(
                    original_command,
                    "_save_all",
                    host,
                    config,
                )
                ws._ensure_apply_button(master, context, ttk_module)

            master.after_idle(add_apply_button)
        return widget

    if build is not None and callable(command) and text == "Wdróż motyw…":
        host, config = build
        original_command = command
        kwargs["command"] = lambda: ws._open_deploy_only(
            _resolve_context(original_command, "_deploy", host, config)
        )

    return self._ttk.Button(master, *args, **kwargs)


setattr(
    _button_with_deferred_context,
    "_giclee_writer_deferred_context",
    True,
)


def install_deferred_context_fix() -> None:
    """Zainstaluj poprawkę raz, zanim wspólny edytor zacznie budować przyciski."""

    current = ws._WriterSafetyTtkProxy.Button
    if getattr(current, "_giclee_writer_deferred_context", False):
        return
    ws._WriterSafetyTtkProxy.Button = _button_with_deferred_context


__all__ = ["install_deferred_context_fix"]
