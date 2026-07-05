"""GUI: Filozofia marki."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES


APP_TITLE = "Filozofia marki — wygląd strony"
_COMPONENT_ID = "filozofiamarki"


def _config():
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Strona Filozofia marki",
        intro_body="Edytujesz sekcje manifestu marki i treści filozofii w szablonie motywu.",
        template_rel="templates/page.filozofia-marki.json",
        preview_path="/pages/filozofia-marki",
        variant_id_prefix="fm",
        zones=PAGE_ZONES,
    )


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1180, 780)
    root.minsize(880, 560)
    build_page_ui(root, _config())
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    build_page_ui(host, _config(), inline=inline)

