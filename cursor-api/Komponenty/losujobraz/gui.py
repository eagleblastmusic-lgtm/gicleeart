"""GUI: Losuj Obraz — szablon strony menu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .registry import PAGE_ZONES

APP_TITLE = "Losuj Obraz — wygląd strony"
_COMPONENT_ID = "losujobraz"
_DRAW_ZONE_ID = "random_artwork_draw"
_MASK_ZONE_ID = "random_artwork_mask"
_ATMOSPHERE_ZONE_ID = "random_artwork_atmosphere"
_V5_SMOKE_ZONE_ID = "random_artwork_v5_smoke"


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


def _open_zone_editor(host: tk.Misc, zone_id: str, missing_message: str) -> None:
    try:
        zone_index = next(
            index for index, zone in enumerate(PAGE_ZONES) if zone.zone_id == zone_id
        )
    except StopIteration:
        messagebox.showerror(APP_TITLE, missing_message, parent=host)
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


def _open_draw_editor(host: tk.Misc) -> None:
    _open_zone_editor(host, _DRAW_ZONE_ID, "Brak strefy Fine Art Oracle.")


def _open_mask_editor(host: tk.Misc) -> None:
    _open_zone_editor(host, _MASK_ZONE_ID, "Brak strefy «Edytowanie Odkrycia maski».")


def _open_atmosphere_editor(host: tk.Misc) -> None:
    _open_zone_editor(host, _ATMOSPHERE_ZONE_ID, "Brak strefy edycji atmosfery.")


def _open_v5_smoke_editor(host: tk.Misc) -> None:
    _open_zone_editor(host, _V5_SMOKE_ZONE_ID, "Brak sekcji dymu kursora V5.")


def _config(host: tk.Misc):
    return build_editor_config(
        module_file=__file__,
        component_id=_COMPONENT_ID,
        app_title=APP_TITLE,
        intro_title="Strona Losuj Obraz (/pages/losuj-produkt)",
        intro_body=(
            "Aktywny wariant: V6 (na bazie V5). Lista «Wersja»: "
            "V1 — podstawowa, V3 — Living Museum Light, V4 — finał muzealny, "
            "V5 — V4 z dymem kursora, V6 — na bazie V5. "
            "W V6 domyślnie jak V5: reflektor wyłączony, pył i dym włączone, parallax włączony. "
            "Pył i dym startują dopiero po zakończeniu animacji złotego okręgu intro. "
            "«Fine Art Oracle…» — teksty i tempo losowania. «Edytuj atmosferę…» — reflektor/pył. "
            "«Dym kursora V5…» — włącznik, preset i parametry fluid. "
            "Przed zapisem tworzona jest kopia zapasowa. Wdróż motyw, aby opublikować."
        ),
        template_rel="templates/page.losuj-produkt.json",
        preview_path="/pages/losuj-produkt",
        variant_id_prefix="lo",
        zones=PAGE_ZONES,
        variant_label_default="V1 — podstawowa",
        extra_toolbar=(
            ("Fine Art Oracle…", lambda: _open_draw_editor(host)),
            ("Edytowanie Odkrycia maski", lambda: _open_mask_editor(host)),
            ("Edytuj atmosferę…", lambda: _open_atmosphere_editor(host)),
            ("Dym kursora V5…", lambda: _open_v5_smoke_editor(host)),
        ),
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
