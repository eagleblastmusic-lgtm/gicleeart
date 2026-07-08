"""GUI: Submenu katalog — panel artystów w nawigacji."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES

APP_TITLE = "Submenu katalog — lista artystów"
_COMPONENT_ID = "submenukatalog"


def _config():
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Submenu Katalog",
        intro_body=(
            "Edytujesz animowaną listę artystów w rozwijanym panelu menu «Katalog». "
            "Konfiguracja trafia do assets/giclee-catalog-submenu-config.json. "
            "Wdróż motyw, aby opublikować na sklepie."
        ),
        template_rel="assets/giclee-catalog-submenu-config.json",
        preview_path="/",
        variant_id_prefix="sk",
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
