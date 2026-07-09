"""Okna «Efekty tekstu…» i «Efekty grafiki…» dla sekcji stron menu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.stronaglowna.effect_form_controls import EffectControlGroup, bind_master_toggle
from Komponenty.stronaglowna.home_effect_panels import build_scroll_reveal_tab
from Komponenty.stronaglowna.section_effects_gui import build_parallax_tab

from .config import PageEditorConfig
from .page_section_effects_settings import (
    PAGE_IMAGE_EFFECT_DEFAULTS,
    load_image_effects_for_section,
    load_text_effects_for_section,
    save_image_effects_for_section,
    save_text_effects_for_section,
    write_page_section_effects_asset,
)
from .types import TemplateZone


def open_text_effects_dialog(
    host: tk.Misc,
    *,
    config: PageEditorConfig,
    variant_id: str,
    zone: TemplateZone,
    app_title: str,
    status_var: tk.StringVar,
) -> None:
    section_key = zone.section_key
    cfg = load_text_effects_for_section(config, variant_id, section_key)

    dlg = tk.Toplevel(host)
    dlg.title(f"Efekty tekstu — {zone.label}")
    dlg.transient(host)
    dlg.grab_set()
    position_toplevel_screen_center(dlg, 580, 720)

    pad = ttk.Frame(dlg, padding=(12, 10))
    pad.pack(fill="both", expand=True)

    ttk.Label(
        pad,
        text="Scroll reveal i hover nagłówka / treści sekcji editorial.",
        font=("", 10, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        pad,
        text=f"Sekcja: {zone.label} · zapis per wariant → {effects_asset_name_hint(config)}",
        wraplength=520,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 8))

    notebook = ttk.Notebook(pad)
    notebook.pack(fill="both", expand=True)

    panel = build_scroll_reveal_tab(
        notebook,
        cfg,
        hook=section_key,
        front_hint=(
            "Na sklepie: efekt tekstu (reveal + hover) dla tej sekcji strony po wdrożeniu motywu."
        ),
    )

    def _save() -> None:
        try:
            collected = panel["collect"]()
            save_text_effects_for_section(config, variant_id, section_key, collected)
            write_page_section_effects_asset(config, variant_id)
        except ValueError as exc:
            messagebox.showerror(app_title, str(exc), parent=dlg)
            return
        except OSError as exc:
            messagebox.showerror(app_title, f"Eksport do motywu nie powiódł się:\n{exc}", parent=dlg)
            return
        status_var.set(f"Zapisano efekty tekstu — «{zone.label}» + asset motywu.")
        show_toast(host, f"Zapisano efekty tekstu — {zone.label}.", duration_ms=1600)
        dlg.destroy()

    def _restore() -> None:
        restore = panel.get("restore_defaults")
        if callable(restore):
            restore()

    btn_row = ttk.Frame(pad)
    btn_row.pack(fill="x", pady=(10, 0))
    ttk.Button(btn_row, text="Przywróć domyślne", command=_restore).pack(side="left")
    ttk.Button(btn_row, text="Anuluj", command=dlg.destroy).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))

    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)


def open_image_effects_dialog(
    host: tk.Misc,
    *,
    config: PageEditorConfig,
    variant_id: str,
    zone: TemplateZone,
    app_title: str,
    status_var: tk.StringVar,
) -> None:
    section_key = zone.section_key
    cfg = load_image_effects_for_section(config, variant_id, section_key)

    dlg = tk.Toplevel(host)
    dlg.title(f"Efekty grafiki — {zone.label}")
    dlg.transient(host)
    dlg.grab_set()
    position_toplevel_screen_center(dlg, 560, 620)

    pad = ttk.Frame(dlg, padding=(12, 10))
    pad.pack(fill="both", expand=True)

    ttk.Label(
        pad,
        text="Parallax i subtelny hover głównej grafiki sekcji.",
        font=("", 10, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        pad,
        text=f"Sekcja: {zone.label} · zapis per wariant → {effects_asset_name_hint(config)}",
        wraplength=520,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 8))

    notebook = ttk.Notebook(pad)
    notebook.pack(fill="both", expand=True)

    parallax_panel = build_parallax_tab(
        notebook,
        cfg,
        tab_label="Parallax grafiki",
    )

    hover_tab = ttk.Frame(notebook, padding=(8, 8))
    notebook.add(hover_tab, text="Hover grafiki")

    hover_enabled_var = tk.BooleanVar(value=bool(cfg.get("imageHoverEnabled", True)))
    hover_scale_var = tk.StringVar(value=str(cfg.get("imageHoverScale", 1.025)))
    hover_duration_var = tk.StringVar(value=str(cfg.get("imageHoverDurationMs", 850)))
    hover_controls = EffectControlGroup()

    ttk.Checkbutton(hover_tab, text="Hover grafiki włączony", variable=hover_enabled_var).pack(
        anchor="w"
    )
    ttk.Label(
        hover_tab,
        text="Delikatne powiększenie zdjęcia przy najechaniu (desktop, fine pointer).",
        wraplength=480,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 10))

    hover_grid = ttk.LabelFrame(hover_tab, text="Parametry hover", padding=(10, 8))
    hover_grid.pack(fill="x")

    scale_lbl = ttk.Label(hover_grid, text="Skala hover:")
    scale_lbl.grid(row=0, column=0, sticky="w", pady=2)
    scale_spin = ttk.Spinbox(
        hover_grid,
        textvariable=hover_scale_var,
        from_=1.0,
        to=1.08,
        increment=0.001,
        width=8,
        format="%.3f",
    )
    scale_spin.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=2)
    duration_lbl = ttk.Label(hover_grid, text="Czas animacji (ms):")
    duration_lbl.grid(row=1, column=0, sticky="w", pady=2)
    duration_spin = ttk.Spinbox(
        hover_grid,
        textvariable=hover_duration_var,
        from_=400,
        to=1600,
        increment=25,
        width=8,
    )
    duration_spin.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=2)
    hover_controls.add_all([scale_lbl, scale_spin, duration_lbl, duration_spin])
    bind_master_toggle(hover_enabled_var, hover_controls)

    def _collect() -> dict[str, Any]:
        merged = dict(PAGE_IMAGE_EFFECT_DEFAULTS)
        merged.update(parallax_panel["collect_parallax"]())
        merged["imageHoverEnabled"] = hover_enabled_var.get()
        try:
            merged["imageHoverScale"] = float(hover_scale_var.get())
        except ValueError:
            merged["imageHoverScale"] = PAGE_IMAGE_EFFECT_DEFAULTS["imageHoverScale"]
        try:
            merged["imageHoverDurationMs"] = int(hover_duration_var.get())
        except ValueError:
            merged["imageHoverDurationMs"] = PAGE_IMAGE_EFFECT_DEFAULTS["imageHoverDurationMs"]
        merged["enabled"] = bool(merged.get("parallaxEnabled")) or bool(merged.get("imageHoverEnabled"))
        return merged

    def _save() -> None:
        try:
            save_image_effects_for_section(config, variant_id, section_key, _collect())
            write_page_section_effects_asset(config, variant_id)
        except ValueError as exc:
            messagebox.showerror(app_title, str(exc), parent=dlg)
            return
        except OSError as exc:
            messagebox.showerror(app_title, f"Eksport do motywu nie powiódł się:\n{exc}", parent=dlg)
            return
        status_var.set(f"Zapisano efekty grafiki — «{zone.label}» + asset motywu.")
        show_toast(host, f"Zapisano efekty grafiki — {zone.label}.", duration_ms=1600)
        dlg.destroy()

    def _restore() -> None:
        defaults = dict(PAGE_IMAGE_EFFECT_DEFAULTS)
        parallax_panel["parallax_var"].set(bool(defaults.get("parallaxEnabled")))
        hover_enabled_var.set(bool(defaults.get("imageHoverEnabled")))
        hover_scale_var.set(str(defaults.get("imageHoverScale")))
        hover_duration_var.set(str(defaults.get("imageHoverDurationMs")))

    btn_row = ttk.Frame(pad)
    btn_row.pack(fill="x", pady=(10, 0))
    ttk.Button(btn_row, text="Przywróć domyślne", command=_restore).pack(side="left")
    ttk.Button(btn_row, text="Anuluj", command=dlg.destroy).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))

    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)


def effects_asset_name_hint(config: PageEditorConfig) -> str:
    from .page_section_effects_settings import effects_asset_basename

    return f"assets/{effects_asset_basename(config)}"
