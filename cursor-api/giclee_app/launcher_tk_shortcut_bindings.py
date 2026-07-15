"""Adapter Tk dla fallbackowych bindingów skrótów launchera."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk


_KEYPRESS_EVENT = "<KeyPress>"
_DEFAULT_BINDING_MARKER = "_giclee_launcher_shortcut_bound"

ShortcutCallback = Callable[[tk.Event], str | None]
DirectBinder = Callable[[tk.Misc], object]


def bind_shortcut_class(
    root: tk.Misc,
    bindtag: str,
    callback: ShortcutCallback,
) -> bool:
    """Rejestruje class binding prywatnego bindtagu launchera."""

    try:
        root.unbind_class(bindtag, _KEYPRESS_EVENT)
    except (AttributeError, tk.TclError):
        pass
    try:
        root.bind_class(bindtag, _KEYPRESS_EVENT, callback)
    except (AttributeError, tk.TclError):
        return False
    return True


def bind_widget_shortcut(
    widget: tk.Misc,
    callback: ShortcutCallback,
    *,
    marker: str = _DEFAULT_BINDING_MARKER,
) -> bool:
    """Dodaje bezpośredni fallback dokładnie raz dla danego widgetu."""

    if getattr(widget, marker, False):
        return False
    try:
        binding_id = widget.bind(_KEYPRESS_EVENT, callback, add="+")
        setattr(widget, marker, binding_id or True)
    except (AttributeError, tk.TclError):
        return False
    return True


def install_shortcut_bindtags(
    root: tk.Misc,
    bindtag: str,
    callback: ShortcutCallback,
    *,
    bind_direct: DirectBinder | None = None,
) -> None:
    """Instaluje bindtag i fallback na aktualnym drzewie widgetów Tk."""

    direct = bind_direct or (
        lambda widget: bind_widget_shortcut(widget, callback)
    )
    stack: list[tk.Misc] = [root]
    while stack:
        widget = stack.pop()

        try:
            children = list(widget.winfo_children())
        except (AttributeError, tk.TclError):
            children = []
        stack.extend(children)

        try:
            current = tuple(str(tag) for tag in widget.bindtags())
            reordered = (bindtag,) + tuple(
                tag for tag in current if tag != bindtag
            )
            if reordered != current:
                widget.bindtags(reordered)
        except (AttributeError, tk.TclError):
            pass

        try:
            direct(widget)
        except (AttributeError, tk.TclError):
            pass
