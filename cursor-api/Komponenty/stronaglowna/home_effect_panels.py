"""GUI panels for individual homepage effect types (one tab each)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .effect_form_controls import EffectControlGroup, bind_master_toggle
from .final_difference_settings import (
    EASING_MODES,
    FINAL_DIFFERENCE_DEFAULTS,
    FINAL_DIFFERENCE_PRESETS,
    PRESET_CUSTOM_LABEL as FD_PRESET_CUSTOM_LABEL,
    apply_final_difference_preset,
)
from .section_effects_gui import build_gradient_bio_tab, build_parallax_tab
from .section_effects_storage import INTRO_HOOK, SEE_DIFFERENCE_HOOK
from .studio_reveal_settings import (
    STUDIO_REVEAL_DEFAULTS,
    STUDIO_REVEAL_PRESETS,
    PRESET_CUSTOM_LABEL as SR_PRESET_CUSTOM_LABEL,
    apply_studio_reveal_preset,
)

_FRONT_ACTIVE_HOOKS: dict[str, frozenset[str]] = {
    "scroll_reveal": frozenset({INTRO_HOOK}),
    "text_hover": frozenset({SEE_DIFFERENCE_HOOK}),
    "gradient_bio": frozenset({INTRO_HOOK, SEE_DIFFERENCE_HOOK, "restoration", "color-correction", "potential", "hero"}),
    "parallax": frozenset({INTRO_HOOK, SEE_DIFFERENCE_HOOK, "restoration", "color-correction", "potential", "hero"}),
}


def _front_status_label(parent: ttk.Frame, hook: str, effect_id: str) -> None:
    active = hook in _FRONT_ACTIVE_HOOKS.get(effect_id, frozenset())
    if active:
        text = "Na sklepie: aktywne po wdrożeniu motywu (obsługa frontu dla tej sekcji)."
        color = "#555"
    else:
        text = (
            "Konfiguracja zapisuje się per sekcja. Front motywu jeszcze nie stosuje tego efektu "
            "dla tej sekcji — po dodaniu obsługi w boot.js zadziała bez zmian w GUI."
        )
        color = "#886600"
    ttk.Label(parent, text=text, wraplength=500, foreground=color).pack(anchor="w", pady=(0, 8))


def build_scroll_reveal_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    hook: str,
    front_hint: str | None = None,
) -> dict[str, Any]:
    tab = ttk.Frame(notebook, padding=(8, 8))
    notebook.add(tab, text="Reveal i hover")

    if front_hint:
        ttk.Label(tab, text=front_hint, wraplength=500, foreground="#555").pack(
            anchor="w", pady=(0, 8)
        )
    else:
        _front_status_label(tab, hook, "scroll_reveal")

    preset_names = list(STUDIO_REVEAL_PRESETS.keys())
    preset_var = tk.StringVar(value=preset_names[0])
    applying_preset = {"active": False}

    enabled_var = tk.BooleanVar(value=bool(cfg["enabled"]))
    desktop_var = tk.BooleanVar(value=bool(cfg["desktopEnabled"]))
    glow_var = tk.BooleanVar(value=bool(cfg["glowEnabled"]))
    easing_var = tk.StringVar(value=str(cfg.get("easing", "museum")))

    preset_row = ttk.Frame(tab)
    preset_row.pack(fill="x", pady=(0, 6))
    preset_label = ttk.Label(preset_row, text="Preset:")
    preset_label.pack(side="left")
    preset_combo = ttk.Combobox(
        preset_row,
        textvariable=preset_var,
        values=preset_names + [SR_PRESET_CUSTOM_LABEL],
        state="readonly",
        width=28,
    )
    preset_combo.pack(side="left", padx=(8, 0))

    param_controls = EffectControlGroup()
    param_controls.add(preset_label)
    param_controls.add(preset_combo, readonly=True)

    enabled_cb = ttk.Checkbutton(tab, text="Reveal i hover włączone", variable=enabled_var)
    enabled_cb.pack(anchor="w")
    desktop_cb = ttk.Checkbutton(tab, text="Aktywne na desktopie (≥750px)", variable=desktop_var)
    desktop_cb.pack(anchor="w")
    glow_cb = ttk.Checkbutton(tab, text="Poświata przy hover tekstu", variable=glow_var)
    glow_cb.pack(anchor="w")
    param_controls.add_all([desktop_cb, glow_cb])

    int_vars: dict[str, tk.StringVar] = {}
    float_vars: dict[str, tk.StringVar] = {}

    reveal_grid = ttk.LabelFrame(tab, text="Scroll reveal i mikrointerakcje", padding=(10, 8))
    reveal_grid.pack(fill="x", pady=(8, 0))

    def _spin_int(parent: ttk.Frame, row: int, key: str, label: str, lo: int, hi: int, step: int) -> None:
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg.get(key, STUDIO_REVEAL_DEFAULTS.get(key, 0))))
        int_vars[key] = var
        spin = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=step, width=8)
        spin.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
        param_controls.add(lbl)
        param_controls.add(spin)

    def _spin_float(parent: ttk.Frame, row: int, key: str, label: str, lo: float, hi: float, step: float) -> None:
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg.get(key, STUDIO_REVEAL_DEFAULTS.get(key, 0))))
        float_vars[key] = var
        spin = ttk.Spinbox(
            parent,
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

    _spin_float(reveal_grid, 0, "revealThreshold", "Próg viewport (0–1):", 0.05, 1.0, 0.05)
    _spin_int(reveal_grid, 1, "cardDurationMs", "Czas karty (ms):", 400, 1800, 25)
    _spin_int(reveal_grid, 2, "textDurationMs", "Czas tekstu (ms):", 400, 1600, 25)
    _spin_int(reveal_grid, 3, "headingDelayMs", "Opóźnienie nagłówka (ms):", 0, 600, 20)
    _spin_int(reveal_grid, 4, "paragraphStaggerMs", "Stagger akapitów (ms):", 0, 400, 10)
    _spin_int(reveal_grid, 5, "bgBrightnessStart", "Przyciemnienie tła start (%):", 50, 100, 1)
    _spin_float(reveal_grid, 6, "lightOpacityMin", "Idle light min (%):", 0.0, 20.0, 0.5)
    _spin_float(reveal_grid, 7, "lightOpacityMax", "Idle light max (%):", 0.0, 20.0, 0.5)
    _spin_float(reveal_grid, 8, "cardHoverScale", "Hover karta scale:", 1.0, 1.05, 0.001)
    _spin_float(reveal_grid, 9, "copyHoverScale", "Hover tekst scale:", 1.0, 1.05, 0.001)
    _spin_int(reveal_grid, 10, "copyHoverTranslateY", "Hover tekst uniesienie (px):", -12, 0, 1)

    easing_row = ttk.Frame(tab)
    easing_row.pack(fill="x", pady=(8, 0))
    easing_label = ttk.Label(easing_row, text="Krzywa easing:")
    easing_label.pack(side="left")
    easing_combo = ttk.Combobox(
        easing_row,
        textvariable=easing_var,
        values=list(EASING_MODES),
        state="readonly",
        width=12,
    )
    easing_combo.pack(side="left", padx=(8, 0))
    param_controls.add(easing_label)
    param_controls.add(easing_combo, readonly=True)

    bind_master_toggle(enabled_var, param_controls)

    def _apply_cfg_to_form(new_cfg: dict[str, Any]) -> None:
        applying_preset["active"] = True
        enabled_var.set(bool(new_cfg.get("enabled", False)))
        desktop_var.set(bool(new_cfg.get("desktopEnabled", True)))
        glow_var.set(bool(new_cfg.get("glowEnabled", True)))
        easing_var.set(str(new_cfg.get("easing", "museum")))
        for key, var in int_vars.items():
            var.set(str(new_cfg.get(key, STUDIO_REVEAL_DEFAULTS.get(key, 0))))
        for key, var in float_vars.items():
            var.set(str(new_cfg.get(key, STUDIO_REVEAL_DEFAULTS.get(key, 0))))
        applying_preset["active"] = False

    def _on_preset_selected(_event: object = None) -> None:
        if applying_preset["active"]:
            return
        name = preset_var.get()
        if name == SR_PRESET_CUSTOM_LABEL:
            return
        merged = dict(STUDIO_REVEAL_DEFAULTS)
        merged.update(apply_studio_reveal_preset(name))
        _apply_cfg_to_form(merged)

    preset_combo.bind("<<ComboboxSelected>>", _on_preset_selected)

    def _mark_custom(*_a: object) -> None:
        if applying_preset["active"]:
            return
        preset_var.set(SR_PRESET_CUSTOM_LABEL)

    for var in list(int_vars.values()) + list(float_vars.values()):
        var.trace_add("write", _mark_custom)
    for trace_var in (enabled_var, desktop_var, glow_var, easing_var):
        trace_var.trace_add("write", _mark_custom)

    def collect() -> dict[str, Any]:
        new_cfg = dict(STUDIO_REVEAL_DEFAULTS)
        new_cfg["enabled"] = enabled_var.get()
        new_cfg["desktopEnabled"] = desktop_var.get()
        new_cfg["glowEnabled"] = glow_var.get()
        new_cfg["easing"] = easing_var.get()
        for key, var in int_vars.items():
            new_cfg[key] = int(var.get())
        for key, var in float_vars.items():
            new_cfg[key] = float(var.get())
        return new_cfg

    def restore_defaults() -> None:
        preset_var.set(preset_names[0])
        merged = dict(STUDIO_REVEAL_DEFAULTS)
        merged.update(apply_studio_reveal_preset(preset_names[0]))
        merged["enabled"] = False
        _apply_cfg_to_form(merged)

    return {"collect": collect, "restore_defaults": restore_defaults}


def build_text_hover_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    hook: str,
) -> dict[str, Any]:
    tab = ttk.Frame(notebook, padding=(8, 8))
    notebook.add(tab, text="Hover tekstu")

    _front_status_label(tab, hook, "text_hover")

    preset_names = list(FINAL_DIFFERENCE_PRESETS.keys())
    preset_var = tk.StringVar(value=preset_names[0])
    applying_preset = {"active": False}

    enabled_var = tk.BooleanVar(value=bool(cfg["enabled"]))
    desktop_var = tk.BooleanVar(value=bool(cfg["desktopEnabled"]))
    glow_var = tk.BooleanVar(value=bool(cfg["glowEnabled"]))
    reverse_var = tk.BooleanVar(value=bool(cfg.get("reverseBehavior", False)))
    easing_var = tk.StringVar(value=str(cfg["easing"]))

    param_controls = EffectControlGroup()

    preset_row = ttk.Frame(tab)
    preset_row.pack(fill="x", pady=(0, 8))
    preset_label = ttk.Label(preset_row, text="Preset:")
    preset_label.pack(side="left")
    preset_combo = ttk.Combobox(
        preset_row,
        textvariable=preset_var,
        values=preset_names + [FD_PRESET_CUSTOM_LABEL],
        state="readonly",
        width=24,
    )
    preset_combo.pack(side="left", padx=(8, 0))
    param_controls.add(preset_label)
    param_controls.add(preset_combo, readonly=True)

    enabled_cb = ttk.Checkbutton(tab, text="Hover tekstu włączony", variable=enabled_var)
    enabled_cb.pack(anchor="w")
    desktop_cb = ttk.Checkbutton(tab, text="Aktywny na desktopie (≥750px)", variable=desktop_var)
    desktop_cb.pack(anchor="w")
    glow_cb = ttk.Checkbutton(tab, text="Poświata pod tekstem", variable=glow_var)
    glow_cb.pack(anchor="w")
    reverse_cb = ttk.Checkbutton(
        tab,
        text="Odwróć działanie (hover na grafikach zamiast tekstu)",
        variable=reverse_var,
    )
    reverse_cb.pack(anchor="w")
    param_controls.add_all([desktop_cb, glow_cb, reverse_cb])

    easing_row = ttk.Frame(tab)
    easing_row.pack(fill="x", pady=(6, 0))
    easing_label = ttk.Label(easing_row, text="Krzywa easing:")
    easing_label.pack(side="left")
    easing_combo = ttk.Combobox(
        easing_row,
        textvariable=easing_var,
        values=list(EASING_MODES),
        state="readonly",
        width=12,
    )
    easing_combo.pack(side="left", padx=(8, 0))
    param_controls.add(easing_label)
    param_controls.add(easing_combo, readonly=True)

    nums = ttk.LabelFrame(tab, text="Parametry hover", padding=(10, 8))
    nums.pack(fill="x", pady=(10, 0))

    int_vars: dict[str, tk.StringVar] = {}
    float_vars: dict[str, tk.StringVar] = {}

    def _spin_int(row: int, key: str, label: str, lo: int, hi: int, step: int) -> None:
        lbl = ttk.Label(nums, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg[key]))
        int_vars[key] = var
        spin = ttk.Spinbox(nums, textvariable=var, from_=lo, to=hi, increment=step, width=8)
        spin.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
        param_controls.add(lbl)
        param_controls.add(spin)

    def _spin_float(row: int, key: str, label: str, lo: float, hi: float, step: float) -> None:
        lbl = ttk.Label(nums, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg[key]))
        float_vars[key] = var
        spin = ttk.Spinbox(
            nums,
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

    bind_master_toggle(enabled_var, param_controls)

    _spin_float(0, "copyScale", "Skala tekstu (hover):", 1.0, 1.12, 0.001)
    _spin_int(1, "copyTranslateY", "Uniesienie tekstu (px):", -24, 0, 1)
    _spin_int(2, "mediaOffsetX", "Cofnięcie grafik (px):", 0, 48, 1)
    _spin_float(3, "mediaScale", "Skala grafik:", 0.9, 1.0, 0.001)
    _spin_int(4, "mediaBrightness", "Jasność grafik (%):", 50, 100, 1)
    _spin_int(5, "bgBrightness", "Jasność tła (%):", 50, 100, 1)
    _spin_int(6, "bgVeilOpacity", "Kurtyna przyciemniająca (%):", 0, 40, 1)
    _spin_int(7, "durationMs", "Czas animacji (ms):", 400, 1600, 25)

    def _apply_cfg_to_form(new_cfg: dict[str, Any]) -> None:
        applying_preset["active"] = True
        enabled_var.set(bool(new_cfg["enabled"]))
        desktop_var.set(bool(new_cfg["desktopEnabled"]))
        glow_var.set(bool(new_cfg["glowEnabled"]))
        reverse_var.set(bool(new_cfg.get("reverseBehavior", False)))
        easing_var.set(str(new_cfg["easing"]))
        for key, var in int_vars.items():
            var.set(str(new_cfg[key]))
        for key, var in float_vars.items():
            var.set(str(new_cfg[key]))
        applying_preset["active"] = False

    def _on_preset_selected(_event: object = None) -> None:
        if applying_preset["active"]:
            return
        name = preset_var.get()
        if name == FD_PRESET_CUSTOM_LABEL:
            return
        _apply_cfg_to_form(apply_final_difference_preset(name))

    preset_combo.bind("<<ComboboxSelected>>", _on_preset_selected)

    def _mark_custom(*_a: object) -> None:
        if applying_preset["active"]:
            return
        preset_var.set(FD_PRESET_CUSTOM_LABEL)

    for var in list(int_vars.values()) + list(float_vars.values()):
        var.trace_add("write", _mark_custom)
    for trace_var in (enabled_var, desktop_var, glow_var, reverse_var, easing_var):
        trace_var.trace_add("write", _mark_custom)

    def collect() -> dict[str, Any]:
        new_cfg = dict(FINAL_DIFFERENCE_DEFAULTS)
        new_cfg["enabled"] = enabled_var.get()
        new_cfg["desktopEnabled"] = desktop_var.get()
        new_cfg["glowEnabled"] = glow_var.get()
        new_cfg["reverseBehavior"] = reverse_var.get()
        new_cfg["easing"] = easing_var.get()
        for key, var in int_vars.items():
            new_cfg[key] = int(var.get())
        for key, var in float_vars.items():
            new_cfg[key] = float(var.get())
        return new_cfg

    def restore_defaults() -> None:
        preset_var.set(preset_names[0])
        merged = dict(FINAL_DIFFERENCE_DEFAULTS)
        merged.update(apply_final_difference_preset(preset_names[0]))
        merged["enabled"] = False
        _apply_cfg_to_form(merged)

    return {"collect": collect, "restore_defaults": restore_defaults}


def build_gradient_bio_effect_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    hook: str,
) -> dict[str, Any]:
    _ = hook
    grad = build_gradient_bio_tab(notebook, cfg)
    return {
        "collect": grad["collect_gradient"],
        "restore_defaults": lambda: grad["apply_preset"](grad["preset_names"][0]),
        "apply_preset": grad["apply_preset"],
        "preset_var": grad["preset_var"],
        "preset_names": grad["preset_names"],
    }


def build_parallax_effect_tab(
    notebook: ttk.Notebook,
    cfg: dict[str, Any],
    *,
    hook: str,
) -> dict[str, Any]:
    _ = hook
    par = build_parallax_tab(notebook, cfg)

    def restore_defaults() -> None:
        par["parallax_var"].set(False)

    return {"collect": par["collect_parallax"], "restore_defaults": restore_defaults}
