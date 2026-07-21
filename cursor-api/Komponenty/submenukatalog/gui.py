"""GUI: Submenu katalog — panel artystów w nawigacji."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from Komponenty._shared.theme_page_editor import gui_shell
from Komponenty._shared.theme_page_editor.bootstrap import build_editor_config, build_page_ui
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .effects import (
    ARTIST_HOVER_EFFECT_FIELD_LABEL,
    ARTIST_HOVER_EFFECT_ID_BY_LABEL,
    ARTIST_HOVER_EFFECT_LABEL_BY_ID,
    ARTIST_HOVER_EFFECT_OPTIONS,
    normalize_artist_hover_effect,
)
from .graphics import (
    PREVIEW_GRAPHICS_VARIANT_FIELD_LABEL,
    PREVIEW_GRAPHICS_VARIANT_ID_BY_LABEL,
    PREVIEW_GRAPHICS_VARIANT_LABEL_BY_ID,
    PREVIEW_GRAPHICS_VARIANT_OPTIONS,
    normalize_preview_graphics_variant,
)
from .registry import PAGE_ZONES

APP_TITLE = "Submenu katalog — lista artystów"
_COMPONENT_ID = "submenukatalog"


class _ThemeEditorTtkProxy:
    """Deleguj ttk, zamieniając wyłącznie pole efektu na readonly Combobox."""

    _giclee_artist_effect_proxy = True

    def __init__(self, ttk_module: Any) -> None:
        self._ttk = ttk_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._ttk, name)

    def Entry(self, master: tk.Misc | None = None, *args: Any, **kwargs: Any) -> ttk.Widget:
        spec = _readonly_combobox_spec(master)
        if spec is None:
            return self._ttk.Entry(master, *args, **kwargs)

        normalizer, options, label_by_id, id_by_label = spec
        technical_var = kwargs.pop("textvariable", None)
        raw_value = technical_var.get() if technical_var is not None else ""
        normalized_id = normalizer(raw_value)
        labels = [label for _item_id, label in options]
        display_var = tk.StringVar(master=master, value=label_by_id[normalized_id])
        width = int(kwargs.pop("width", 34) or 34)
        combo = self._ttk.Combobox(
            master,
            *args,
            textvariable=display_var,
            values=labels,
            state="readonly",
            width=max(28, width),
            **kwargs,
        )

        def _write_choice(_event: tk.Event | None = None) -> None:
            if technical_var is None:
                return
            technical_var.set(
                id_by_label.get(display_var.get(), normalizer(technical_var.get()))
            )

        def _sync_display(*_args: object) -> None:
            if technical_var is None:
                return
            normalized = normalizer(technical_var.get())
            expected = label_by_id[normalized]
            if display_var.get() != expected:
                display_var.set(expected)

        combo.bind("<<ComboboxSelected>>", _write_choice)
        if technical_var is not None:
            technical_var.trace_add("write", _sync_display)
            if str(raw_value or "").strip().lower() != normalized_id:
                combo.after_idle(lambda: technical_var.set(normalized_id))

        combo._giclee_effect_display_var = display_var  # type: ignore[attr-defined]
        return combo



def _field_with_label(master: tk.Misc | None, label: str) -> bool:
    if master is None:
        return False
    try:
        recent_children = master.winfo_children()[-4:]
    except (AttributeError, tk.TclError):
        return False
    for child in recent_children:
        try:
            if child.winfo_class() == "TLabel" and child.cget("text") == label:
                return True
        except (AttributeError, tk.TclError):
            continue
    return False


def _is_artist_effect_field(master: tk.Misc | None) -> bool:
    return _field_with_label(master, ARTIST_HOVER_EFFECT_FIELD_LABEL)


def _is_preview_graphics_field(master: tk.Misc | None) -> bool:
    return _field_with_label(master, PREVIEW_GRAPHICS_VARIANT_FIELD_LABEL)


def _readonly_combobox_spec(master: tk.Misc | None):
    if _is_artist_effect_field(master):
        return (
            normalize_artist_hover_effect,
            ARTIST_HOVER_EFFECT_OPTIONS,
            ARTIST_HOVER_EFFECT_LABEL_BY_ID,
            ARTIST_HOVER_EFFECT_ID_BY_LABEL,
        )
    if _is_preview_graphics_field(master):
        return (
            normalize_preview_graphics_variant,
            PREVIEW_GRAPHICS_VARIANT_OPTIONS,
            PREVIEW_GRAPHICS_VARIANT_LABEL_BY_ID,
            PREVIEW_GRAPHICS_VARIANT_ID_BY_LABEL,
        )
    return None

def _install_artist_effect_renderer() -> None:
    current = gui_shell.ttk
    if getattr(current, "_giclee_artist_effect_proxy", False):
        return
    gui_shell.ttk = _ThemeEditorTtkProxy(current)


def _install_section_effects_asset_guard() -> None:
    """Nie generuj pustego *-section-effects.js dla komponentu ustawieniowego.

    Wspólna powłoka zapisuje taki asset po każdym Save/Deploy. Submenu katalog
    nie ma stref efektów sekcji, więc bezpiecznie pomijamy wyłącznie ten jeden
    komponent, a wszystkie pozostałe delegujemy do oryginalnej funkcji.
    """

    current = gui_shell.write_page_section_effects_asset
    if getattr(current, "_giclee_catalog_section_effects_guard", False):
        return

    def guarded_write_page_section_effects_asset(config: Any, variant_id: str) -> Any:
        if getattr(config, "component_id", "") == _COMPONENT_ID:
            return None
        return current(config, variant_id)

    guarded_write_page_section_effects_asset._giclee_catalog_section_effects_guard = True  # type: ignore[attr-defined]
    guarded_write_page_section_effects_asset._giclee_original = current  # type: ignore[attr-defined]
    gui_shell.write_page_section_effects_asset = guarded_write_page_section_effects_asset


def _install_component_overrides() -> None:
    _install_artist_effect_renderer()
    _install_section_effects_asset_guard()


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
    _install_component_overrides()
    build_page_ui(root, _config())
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    _install_component_overrides()
    build_page_ui(host, _config(), inline=inline)
