"""GUI: Własna fotografia."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES


APP_TITLE = "Własna fotografia — szablon PDP"
_COMPONENT_ID = "wlasnafotografia"


def _config():
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Własna fotografia — PDP",
        intro_body="Edytujesz szablon produktu (mockup w motywie + Worker). Menu kieruje na PDP, nie na page.fotografia-obraz.",
        template_rel="templates/product.szablon-wlasna-fotografia.json",
        preview_path="/products/twoje-zdjecie-jako-wydruk-giclee-na-papierze-fine-art-w-drewnianej-ramie",
        variant_id_prefix="wf",
        zones=PAGE_ZONES,
    )


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1100, 720)
    root.minsize(880, 560)
    build_page_ui(root, _config())
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    build_page_ui(host, _config(), inline=inline)

