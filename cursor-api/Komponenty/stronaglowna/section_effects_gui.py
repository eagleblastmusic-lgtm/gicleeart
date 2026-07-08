"""Wspólne widgety GUI — zakładki efektów homepage (gradient BIO, parallax, reveal…)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .effect_form_controls import EffectControlGroup, bind_master_toggle
from .section_bg_effects_settings import (
    SECTION_BG_EFFECTS_DEFAULTS,
    SECTION_BG_EFFECTS_PRESETS,
    apply_section_bg_effects_preset,
)
from .studio_reveal_settings import GRADIENT_PRESETS, PRESET_CUSTOM_LABEL


def build_gradient_bio_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    tab_label: str = "Gradient BIO",
    on_mark_custom: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Zakładka gradientu BIO — osobno od parallax."""
    enabled_var = tk.BooleanVar(
        value=bool(cfg.get("enabled", False)) and str(cfg.get("gradientPreset", "none")) != "none"
    )
    desktop_var = tk.BooleanVar(value=bool(cfg.get("desktopEnabled", True)))
    gradient_var = tk.StringVar(
        value=str(cfg.get("gradientPreset", "none") if enabled_var.get() else "none")
    )

    tab = ttk.Frame(notebook, padding=(8, 8))
    notebook.add(tab, text=tab_label)

    int_vars: dict[str, tk.StringVar] = {}

    preset_names = list(SECTION_BG_EFFECTS_PRESETS.keys())
    preset_var = tk.StringVar(value=preset_names[0])

    param_controls = EffectControlGroup()

    enabled_cb = ttk.Checkbutton(tab, text="Gradient BIO włączony", variable=enabled_var)
    enabled_cb.pack(anchor="w")
    desktop_cb = ttk.Checkbutton(tab, text="Aktywny na desktopie (≥750px)", variable=desktop_var)
    desktop_cb.pack(anchor="w")
    param_controls.add(desktop_cb)

    preset_row = ttk.Frame(tab)
    preset_row.pack(fill="x", pady=(8, 6))
    preset_label = ttk.Label(preset_row, text="Preset:")
    preset_label.pack(side="left")
    preset_combo = ttk.Combobox(
        preset_row,
        textvariable=preset_var,
        values=preset_names + [PRESET_CUSTOM_LABEL],
        state="readonly",
        width=26,
    )
    preset_combo.pack(side="left", padx=(8, 0))
    param_controls.add(preset_label)
    param_controls.add(preset_combo, readonly=True)

    grad_row = ttk.Frame(tab)
    grad_row.pack(fill="x", pady=(0, 8))
    grad_label = ttk.Label(grad_row, text="Typ gradientu:")
    grad_label.pack(side="left")
    grad_combo = ttk.Combobox(
        grad_row,
        textvariable=gradient_var,
        values=list(GRADIENT_PRESETS),
        state="readonly",
        width=18,
    )
    grad_combo.pack(side="left", padx=(8, 0))
    param_controls.add(grad_label)
    param_controls.add(grad_combo, readonly=True)

    hint_label = ttk.Label(
        tab,
        text="Presety jak w biografii kolekcji: editorial, menu_wide/narrow, radial_spot.",
        wraplength=480,
        foreground="#555",
    )
    hint_label.pack(anchor="w", pady=(0, 8))
    param_controls.add(hint_label)

    grad_grid = ttk.LabelFrame(tab, text="Parametry gradientu", padding=(10, 8))
    grad_grid.pack(fill="x")

    def _spin_int(row: int, key: str, label: str, lo: int, hi: int, step: int) -> None:
        lbl = ttk.Label(grad_grid, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg.get(key, SECTION_BG_EFFECTS_DEFAULTS[key])))
        int_vars[key] = var
        spin = ttk.Spinbox(grad_grid, textvariable=var, from_=lo, to=hi, increment=step, width=8)
        spin.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
        param_controls.add(lbl)
        param_controls.add(spin)

    _spin_int(0, "gradientOverlayOpacity", "Siła overlay (%):", 0, 100, 2)
    _spin_int(1, "radialCenterX", "Radial — środek X (%):", 0, 100, 1)
    _spin_int(2, "radialCenterY", "Radial — środek Y (%):", 0, 100, 1)
    _spin_int(3, "radialRadiusX", "Radial — promień X (%):", 20, 120, 1)
    _spin_int(4, "radialRadiusY", "Radial — promień Y (%):", 20, 120, 1)
    _spin_int(5, "radialFeather", "Radial — feather (%):", 0, 100, 1)
    _spin_int(6, "radialExposure", "Radial — ekspozycja (%):", 0, 100, 1)

    bind_master_toggle(enabled_var, param_controls)

    applying = {"active": False}

    def _apply_preset(name: str) -> None:
        applying["active"] = True
        new_cfg = apply_section_bg_effects_preset(name)
        enabled_var.set(bool(new_cfg["enabled"]))
        desktop_var.set(bool(new_cfg["desktopEnabled"]))
        gradient_var.set(str(new_cfg["gradientPreset"]))
        for key, var in int_vars.items():
            var.set(str(new_cfg[key]))
        applying["active"] = False

    def _on_preset(_event: object = None) -> None:
        if applying["active"]:
            return
        name = preset_var.get()
        if name == PRESET_CUSTOM_LABEL:
            return
        _apply_preset(name)
        if on_mark_custom:
            on_mark_custom()

    preset_combo.bind("<<ComboboxSelected>>", _on_preset)

    def _trace_custom(*_a: object) -> None:
        if applying["active"]:
            return
        preset_var.set(PRESET_CUSTOM_LABEL)
        if on_mark_custom:
            on_mark_custom()

    for var in int_vars.values():
        var.trace_add("write", _trace_custom)
    for trace_var in (enabled_var, desktop_var, gradient_var):
        trace_var.trace_add("write", _trace_custom)

    def collect_gradient() -> dict[str, Any]:
        gradient_on = bool(enabled_var.get())
        preset = str(gradient_var.get() if gradient_on else "none")
        out: dict[str, Any] = {"desktopEnabled": desktop_var.get(), "gradientPreset": preset}
        for key, var in int_vars.items():
            out[key] = int(var.get())
        return out

    return {
        "collect_gradient": collect_gradient,
        "apply_preset": _apply_preset,
        "preset_var": preset_var,
        "preset_names": preset_names,
        "enabled_var": enabled_var,
    }


def build_parallax_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    tab_label: str = "Parallax tła",
    on_mark_custom: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Zakładka parallax — osobno od gradientu."""
    parallax_var = tk.BooleanVar(value=bool(cfg.get("parallaxEnabled", False)))

    tab = ttk.Frame(notebook, padding=(8, 8))
    notebook.add(tab, text=tab_label)

    int_vars: dict[str, tk.StringVar] = {}
    float_vars: dict[str, tk.StringVar] = {}
    param_controls = EffectControlGroup()

    parallax_cb = ttk.Checkbutton(tab, text="Parallax tła włączony (mysz, desktop)", variable=parallax_var)
    parallax_cb.pack(anchor="w", pady=(0, 8))

    hint_label = ttk.Label(
        tab,
        text="Subtelny ruch tła od kursora. Wyłączony na mobile i przy prefers-reduced-motion.",
        wraplength=480,
        foreground="#555",
    )
    hint_label.pack(anchor="w", pady=(0, 8))
    param_controls.add(hint_label)

    grid = ttk.LabelFrame(tab, text="Parametry parallax", padding=(10, 8))
    grid.pack(fill="x")

    def _spin_int(row: int, key: str, label: str, lo: int, hi: int, step: int) -> None:
        lbl = ttk.Label(grid, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg.get(key, SECTION_BG_EFFECTS_DEFAULTS[key])))
        int_vars[key] = var
        spin = ttk.Spinbox(grid, textvariable=var, from_=lo, to=hi, increment=step, width=8)
        spin.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
        param_controls.add(lbl)
        param_controls.add(spin)

    def _spin_float(row: int, key: str, label: str, lo: float, hi: float, step: float) -> None:
        lbl = ttk.Label(grid, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg.get(key, SECTION_BG_EFFECTS_DEFAULTS[key])))
        float_vars[key] = var
        spin = ttk.Spinbox(
            grid,
            textvariable=var,
            from_=lo,
            to=hi,
            increment=step,
            width=8,
            format="%.3f",
        )
        spin.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
        param_controls.add(lbl)
        param_controls.add(spin)

    bind_master_toggle(parallax_var, param_controls)

    _spin_int(0, "parallaxMaxX", "Max przesunięcie X (px):", 0, 40, 1)
    _spin_int(1, "parallaxMaxY", "Max przesunięcie Y (px):", 0, 28, 1)
    _spin_float(2, "parallaxEase", "Wygładzanie (lerp):", 0.03, 0.15, 0.005)
    _spin_int(3, "parallaxOverscan", "Overscan tła (%):", 100, 112, 1)

    def _trace_custom(*_a: object) -> None:
        if on_mark_custom:
            on_mark_custom()

    for var in list(int_vars.values()) + list(float_vars.values()):
        var.trace_add("write", _trace_custom)
    parallax_var.trace_add("write", _trace_custom)

    def collect_parallax() -> dict[str, Any]:
        out: dict[str, Any] = {"parallaxEnabled": parallax_var.get()}
        for key, var in int_vars.items():
            out[key] = int(var.get())
        for key, var in float_vars.items():
            out[key] = float(var.get())
        return out

    return {"collect_parallax": collect_parallax, "parallax_var": parallax_var}


def build_gradient_parallax_notebook_tabs(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    on_mark_custom: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Gradient BIO + Parallax — dwie osobne zakładki; enabled = gradient lub parallax."""
    grad = build_gradient_bio_tab(notebook, cfg, on_mark_custom=on_mark_custom)
    par = build_parallax_tab(notebook, cfg, on_mark_custom=on_mark_custom)

    def collect() -> dict[str, Any]:
        merged = dict(SECTION_BG_EFFECTS_DEFAULTS)
        g = grad["collect_gradient"]()
        p = par["collect_parallax"]()
        merged.update(g)
        merged.update(p)
        gradient_on = str(merged.get("gradientPreset", "none")) != "none" and bool(
            grad["enabled_var"].get()
        )
        parallax_on = bool(p.get("parallaxEnabled"))
        merged["enabled"] = gradient_on or parallax_on
        if not gradient_on:
            merged["gradientPreset"] = "none"
        return merged

    def apply_preset(name: str) -> None:
        grad["apply_preset"](name)

    return {
        "enabled_var": grad["enabled_var"],
        "collect": collect,
        "apply_preset": apply_preset,
        "preset_var": grad["preset_var"],
        "preset_names": grad["preset_names"],
    }
