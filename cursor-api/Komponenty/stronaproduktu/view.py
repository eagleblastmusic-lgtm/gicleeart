"""Widok inline — Strona produktu w launcherze GicleeApp."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from Komponenty._shared.inline_view_shell import mount_inline_view
from Komponenty._shared.window_geometry import attach_onscreen_guard

from .gui_ai import APP_TITLE, _build_ui


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    try:
        attach_onscreen_guard(parent.winfo_toplevel(), fallback_width=1360, fallback_height=920)
    except tk.TclError:
        pass
    return mount_inline_view(
        parent,
        on_back,
        title=APP_TITLE,
        build_content=lambda frame: _build_ui(frame, inline=True),
    )
