"""GUI: Losuj Obraz — szablon strony menu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES

APP_TITLE = "Losuj Obraz — wygląd strony"
_COMPONENT_ID = "losujobraz"
_ATMOSPHERE_ZONE_ID = "random_artwork_atmosphere"


def _walk_widgets(widget: tk.Misc):
    for child in widget.winfo_children():
        yield child
        yield from _walk_widgets(child)


def _is_page_zone_list(widget: tk.Listbox) -> bool:
    try:
        rows = tuple(str(value).removesuffix(" [wył.]") for value in widget.get(0, "end"))
    except tk.TclError:
        return False
    return rows == tuple(zone.label for zone in PAGE_ZONES)


def _open_atmosphere_editor(host: tk.Misc) -> None:
    try:
        zone_index = next(
            index for index, zone in enumerate(PAGE_ZONES) if zone.zone_id == _ATMOSPHERE_ZONE_ID
        )
    except StopIteration:
        messagebox.showerror(APP_TITLE, "Brak strefy edycji atmosfery.", parent=host)
        return

    for widget in _walk_widgets(host):
        if not isinstance(widget, tk.Listbox) or not _is_page_zone_list(widget):
            continue
        try:
            widget.selection_clear(0, "end")
            widget.selection_set(zone_index)
            widget.activate(zone_index)
            widget.see(zone_index)
            widget.event_generate("<<ListboxSelect>>")
            widget.focus_set()
            return
        except tk.TclError:
            continue

    messagebox.showwarning(
        APP_TITLE,
        "Panel sekcji nie jest jeszcze gotowy. Otwórz ponownie moduł Losuj Obraz.",
        parent=host,
    )


def _config(host: tk.Misc):
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Strona Losuj Obraz (/pages/losuj-produkt)",
        intro_body=(
            "Lista «Wersja» wybiera design: V1 — podstawowa, V2 — atmosfera muzealna, "
            "V3 — Living Museum Light oraz V4 — finał muzealny. V4 zachowuje scenę i "
            "atmosferę V3, ale dodaje płynniejsze wyłonienie zwycięskiego obrazu, lżejszą "
            "oprawę, muzealną typografię i hierarchię akcji. Przycisk «Edytuj atmosferę…» "
            "otwiera ustawienia V2 oraz Living Museum Light dla V3/V4. Edytujesz też treści "
            "sekcji w templates/page.losuj-produkt.json. Przed zapisem tworzona jest kopia "
            "zapasowa. Wdróż motyw, aby opublikować na sklepie."
        ),
        template_rel="templates/page.losuj-produkt.json",
        preview_path="/pages/losuj-produkt",
        variant_id_prefix="lo",
        zones=PAGE_ZONES,
        variant_label_default="V1 — podstawowa",
        extra_toolbar=(("Edytuj atmosferę…", lambda: _open_atmosphere_editor(host)),),
    )


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1100, 720)
    root.minsize(880, 560)
    build_page_ui(root, _config(root))
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    build_page_ui(host, _config(host), inline=inline)
