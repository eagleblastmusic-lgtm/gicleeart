"""Okna «Efekty tekstu…» i «Efekty grafiki…» dla sekcji stron menu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.stronaglowna.effect_form_controls import EffectControlGroup, bind_master_toggle
from Komponenty.stronaglowna.home_effect_panels import build_scroll_reveal_tab

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


def _build_image_parallax_slider_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    tab_label: str,
) -> dict[str, Any]:
    """Panel parallax grafiki z niezależnymi suwakami ruchu i powrotu."""

    parallax_var = tk.BooleanVar(value=bool(cfg.get("parallaxEnabled", False)))
    tab = ttk.Frame(notebook, padding=(8, 8))
    notebook.add(tab, text=tab_label)

    parallax_cb = ttk.Checkbutton(
        tab,
        text="Parallax grafiki włączony (mysz, desktop)",
        variable=parallax_var,
    )
    parallax_cb.pack(anchor="w", pady=(0, 8))

    hint_label = ttk.Label(
        tab,
        text="Subtelny ruch grafiki od kursora. Wyłączony na mobile i przy prefers-reduced-motion.",
        wraplength=540,
        foreground="#555",
    )
    hint_label.pack(anchor="w", pady=(0, 8))

    grid = ttk.LabelFrame(tab, text="Parametry parallax", padding=(10, 10))
    grid.pack(fill="x")
    grid.columnconfigure(1, weight=1)

    slider_vars: dict[str, tk.DoubleVar] = {}
    int_keys = {"parallaxMaxX", "parallaxMaxY", "parallaxOverscan"}
    float_keys = {"parallaxEase", "parallaxReturnEase"}
    param_controls = EffectControlGroup()

    def _slider(
        row: int,
        key: str,
        label: str,
        lo: float,
        hi: float,
        *,
        decimals: int,
    ) -> None:
        raw_value = cfg.get(key, PAGE_IMAGE_EFFECT_DEFAULTS[key])
        try:
            initial = float(raw_value)
        except (TypeError, ValueError):
            initial = float(PAGE_IMAGE_EFFECT_DEFAULTS[key])
        initial = max(lo, min(hi, initial))

        value_var = tk.DoubleVar(value=initial)
        display_var = tk.StringVar()
        slider_vars[key] = value_var

        lbl = ttk.Label(grid, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=5)

        scale = ttk.Scale(
            grid,
            variable=value_var,
            from_=lo,
            to=hi,
            orient="horizontal",
        )
        scale.grid(row=row, column=1, sticky="ew", padx=(12, 10), pady=5)

        value_lbl = ttk.Label(grid, textvariable=display_var, width=7, anchor="e")
        value_lbl.grid(row=row, column=2, sticky="e", pady=5)

        def _sync_display(*_args: object) -> None:
            value = max(lo, min(hi, float(value_var.get())))
            if decimals:
                display_var.set(f"{value:.{decimals}f}")
            else:
                display_var.set(str(int(round(value))))

        value_var.trace_add("write", _sync_display)
        _sync_display()
        param_controls.add_all([lbl, scale, value_lbl])

    _slider(0, "parallaxMaxX", "Max przesunięcie X (px):", 0, 40, decimals=0)
    _slider(1, "parallaxMaxY", "Max przesunięcie Y (px):", 0, 28, decimals=0)
    _slider(2, "parallaxEase", "Wygładzanie ruchu (lerp):", 0.03, 0.15, decimals=3)
    _slider(
        3,
        "parallaxReturnEase",
        "Wygładzanie powrotu (lerp):",
        0.01,
        0.10,
        decimals=3,
    )
    _slider(4, "parallaxOverscan", "Overscan grafiki (%):", 100, 112, decimals=0)

    instructions = ttk.LabelFrame(tab, text="Jak regulować", padding=(10, 8))
    instructions.pack(fill="x", pady=(10, 0))
    ttk.Label(
        instructions,
        text=(
            "• Max X / Y — określa siłę przesunięcia grafiki.\n"
            "• Wygładzanie ruchu — niżej = wolniejsze podążanie za kursorem.\n"
            "• Wygładzanie powrotu — niżej = łagodniejszy powrót po wyjechaniu kursora.\n"
            "• Overscan — zapas powiększenia; zwiększ, jeśli przy ruchu widać krawędzie.\n"
            "Polecany punkt startowy: X 16 · Y 10 · ruch 0.075 · powrót 0.035 · overscan 106."
        ),
        wraplength=540,
        justify="left",
        foreground="#555",
    ).pack(anchor="w")
    param_controls.add(hint_label)
    bind_master_toggle(parallax_var, param_controls)

    def collect_parallax() -> dict[str, Any]:
        out: dict[str, Any] = {"parallaxEnabled": parallax_var.get()}
        for key in int_keys:
            out[key] = int(round(slider_vars[key].get()))
        for key in float_keys:
            out[key] = round(float(slider_vars[key].get()), 3)
        return out

    def restore_defaults() -> None:
        parallax_var.set(bool(PAGE_IMAGE_EFFECT_DEFAULTS["parallaxEnabled"]))
        for key, var in slider_vars.items():
            var.set(float(PAGE_IMAGE_EFFECT_DEFAULTS[key]))

    return {
        "collect_parallax": collect_parallax,
        "parallax_var": parallax_var,
        "restore_defaults": restore_defaults,
    }


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
    image_field = next((field for field in zone.fields if field.kind == "shopify_image"), None)

    dlg = tk.Toplevel(host)
    dlg.title(f"Efekty grafiki — {zone.label}")
    dlg.transient(host)
    dlg.grab_set()
    position_toplevel_screen_center(dlg, 620, 680)

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
    ).pack(anchor="w", pady=(4, 2))
    if image_field is not None:
        ttk.Label(
            pad,
            text=f"Grafika: {image_field.label}",
            wraplength=520,
            foreground="#666",
        ).pack(anchor="w", pady=(0, 8))
    else:
        ttk.Label(pad, text="", padding=0).pack(anchor="w", pady=(0, 6))

    notebook = ttk.Notebook(pad)
    notebook.pack(fill="both", expand=True)

    parallax_panel = _build_image_parallax_slider_tab(
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
        parallax_panel["restore_defaults"]()
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
