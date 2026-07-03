"""Widok inline — Karuzela w launcherze GicleeApp."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from Komponenty._shared.inline_view_shell import mount_inline_view

from .gui import APP_TITLE, _build_ui


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    return mount_inline_view(
        parent,
        on_back,
        title=APP_TITLE,
        build_content=lambda frame: _build_ui(frame, inline=True),
    )
