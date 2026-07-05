"""GUI: Katalog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES

import subprocess
import sys
from pathlib import Path


APP_TITLE = "Katalog — wygląd kolekcji"
_COMPONENT_ID = "katalog"


def _config():
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Katalog — strony kolekcji",
        intro_body="Edytujesz layout stron artystów (collection.json). Listę artystów w menu zarządzasz w Dodaj obraz.",
        template_rel="templates/collection.json",
        preview_path="/collections",
        variant_id_prefix="ka",
        zones=PAGE_ZONES,
        extra_toolbar=(("Zarządzaj artystami →", _open_dodajobraz),),
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


def _open_dodajobraz() -> None:
    root = Path(__file__).resolve().parents[2]
    subprocess.Popen([sys.executable, "-m", "Komponenty.dodajobraz"], cwd=str(root))

