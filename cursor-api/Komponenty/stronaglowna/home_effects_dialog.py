"""Uniwersalne okna efektów strony głównej — jeden przycisk, zakładki per typ efektu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .home_effects_registry import save_all_effects_for_hook, sorted_effect_types
from .homepage_variants import set_variant_home_stack, variant_label, variant_uses_home_stack
from .registry import HOME_ZONES, ZONE_HOME_HOOK, HomeZone, zone_by_id
from .scroll_settings import (
    MOBILE_MODES,
    PRESET_CUSTOM_LABEL,
    REDUCED_MOTION_MODES,
    SCROLL_DEFAULTS,
    SCROLL_PRESETS,
    apply_scroll_preset,
    load_scroll_config,
    save_scroll_config,
    validate_scroll_config,
)
from .effect_form_controls import EffectControlGroup, bind_master_toggle
from .final_difference_settings import load_final_difference_config
from .section_bg_effects_settings import load_section_bg_effects_config
from .studio_reveal_settings import load_studio_reveal_config


def effect_zones() -> list[HomeZone]:
    out: list[HomeZone] = []
    for zone in HOME_ZONES:
        if zone.settings_only:
            continue
        if ZONE_HOME_HOOK.get(zone.zone_id):
            out.append(zone)
    return out


def zone_hook(zone_id: str) -> str | None:
    return ZONE_HOME_HOOK.get(zone_id)


def open_section_effects_dialog(
    host: tk.Misc,
    *,
    variant_id: str,
    initial_zone_id: str | None,
    app_title: str,
    export_home_assets: Callable[..., None],
    status_var: tk.StringVar,
) -> None:
    zones = effect_zones()
    if not zones:
        return

    zone_by_label = {z.label: z for z in zones}
    labels = [z.label for z in zones]
    initial_zone = zone_by_id(initial_zone_id) if initial_zone_id else zones[0]
    if initial_zone not in zones:
        initial_zone = zones[0]

    dlg = tk.Toplevel(host)
    dlg.title(f"Efekty — {variant_label(variant_id)}")
    dlg.transient(host)
    dlg.grab_set()
    position_toplevel_screen_center(dlg, 620, 760)

    pad = ttk.Frame(dlg, padding=(12, 10))
    pad.pack(fill="both", expand=True)

    ttk.Label(
        pad,
        text="Efekty sekcji — wszystkie typy dostępne dla każdej sekcji",
        font=("", 10, "bold"),
    ).pack(anchor="w")

    selector_row = ttk.Frame(pad)
    selector_row.pack(fill="x", pady=(8, 6))
    ttk.Label(selector_row, text="Sekcja:").pack(side="left")
    section_var = tk.StringVar(value=initial_zone.label)
    section_combo = ttk.Combobox(
        selector_row,
        textvariable=section_var,
        values=labels,
        state="readonly",
        width=32,
    )
    section_combo.pack(side="left", padx=(8, 0))

    ttk.Label(
        pad,
        text=(
            "Każda zakładka to osobny pakiet efektów (reveal, hover, gradient, parallax…). "
            "Zapis per wariant → assets/giclee-home-sections.js."
        ),
        wraplength=540,
        foreground="#555",
    ).pack(anchor="w", pady=(0, 8))

    notebook_host = ttk.Frame(pad)
    notebook_host.pack(fill="both", expand=True)
    notebook = ttk.Notebook(notebook_host)
    notebook.pack(fill="both", expand=True)

    panels: dict[str, dict[str, Any]] = {}
    current_hook = {"value": zone_hook(initial_zone.zone_id) or ""}

    def _rebuild_panels() -> None:
        for child in notebook.winfo_children():
            child.destroy()
        panels.clear()
        hook = current_hook["value"]
        if not hook:
            return
        for effect in sorted_effect_types():
            cfg = effect.load_for_hook(variant_id, hook)
            panels[effect.effect_id] = effect.build_tab(notebook, cfg, hook)

    _rebuild_panels()

    def _on_section_change(_event: object = None) -> None:
        zone = zone_by_label.get(section_var.get())
        if not zone:
            return
        hook = zone_hook(zone.zone_id)
        if not hook:
            return
        current_hook["value"] = hook
        _rebuild_panels()

    section_combo.bind("<<ComboboxSelected>>", _on_section_change)

    def _collect_all() -> dict[str, dict[str, Any]]:
        return {effect_id: panel["collect"]() for effect_id, panel in panels.items()}

    def _validate_all(collected: dict[str, dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        for effect in sorted_effect_types():
            cfg = collected.get(effect.effect_id)
            if cfg is None:
                continue
            errors.extend(effect.validate(cfg))
        return errors

    def _save() -> None:
        hook = current_hook["value"]
        if not hook:
            return
        collected = _collect_all()
        errors = _validate_all(collected)
        if errors:
            messagebox.showerror(app_title, "\n".join(errors), parent=dlg)
            return
        try:
            save_all_effects_for_hook(variant_id, hook, collected)
        except ValueError as exc:
            messagebox.showerror(app_title, str(exc), parent=dlg)
            return

        zone = zone_by_label.get(section_var.get())
        zone_label = zone.label if zone else hook

        try:
            export_home_assets(
                studio_reveal_config=load_studio_reveal_config(variant_id),
                final_difference_config=load_final_difference_config(variant_id),
                section_bg_effects_config=load_section_bg_effects_config(variant_id),
            )
        except Exception as exc:
            messagebox.showerror(app_title, f"Eksport do motywu nie powiódł się:\n{exc}", parent=dlg)
            return

        status_var.set(f"Zapisano efekty sekcji «{zone_label}» + assets motywu.")
        show_toast(host, f"Zapisano efekty — {zone_label}.", duration_ms=1600)

    def _restore_current_tab() -> None:
        try:
            idx = notebook.index(notebook.select())
        except tk.TclError:
            return
        effect_ids = [e.effect_id for e in sorted_effect_types()]
        if idx < 0 or idx >= len(effect_ids):
            return
        panel = panels.get(effect_ids[idx])
        if panel and callable(panel.get("restore_defaults")):
            panel["restore_defaults"]()

    btn_row = ttk.Frame(pad)
    btn_row.pack(fill="x", pady=(10, 0))
    ttk.Button(btn_row, text="Przywróć domyślne (ta zakładka)", command=_restore_current_tab).pack(side="left")
    ttk.Button(btn_row, text="Anuluj", command=dlg.destroy).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))

    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)


def open_transitions_dialog(
    host: tk.Misc,
    *,
    variant_id: str,
    initial_tab: int,
    app_title: str,
    export_home_assets: Callable[..., None],
    status_var: tk.StringVar,
    open_preview: Callable[[], None] | None = None,
) -> None:
    dlg = tk.Toplevel(host)
    dlg.title(f"Przejścia — {variant_label(variant_id)}")
    dlg.transient(host)
    dlg.grab_set()
    position_toplevel_screen_center(dlg, 620, 720)

    notebook = ttk.Notebook(dlg)
    notebook.pack(fill="both", expand=True, padx=12, pady=(12, 0))
    try:
        notebook.select(initial_tab)
    except tk.TclError:
        pass

    tab_scroll = ttk.Frame(notebook, padding=(14, 12))
    tab_stack = ttk.Frame(notebook, padding=(14, 12))
    notebook.add(tab_scroll, text="Między sekcjami")
    notebook.add(tab_stack, text="Warstwy (stack)")

    cfg = load_scroll_config(variant_id)
    stack_on = variant_uses_home_stack(variant_id)

    pad = tab_scroll
    ttk.Label(pad, text="Section-scroll", font=("", 10, "bold")).pack(anchor="w")
    ttk.Label(
        pad,
        text="Jeden gest przewija do kolejnej sekcji strony głównej.",
        wraplength=520,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 10))

    preset_names = list(SCROLL_PRESETS.keys())
    preset_var = tk.StringVar(value=preset_names[0])
    applying_preset = {"active": False}

    preset_row = ttk.Frame(pad)
    preset_row.pack(fill="x", pady=(0, 8))
    preset_label = ttk.Label(preset_row, text="Preset:")
    preset_label.pack(side="left")
    preset_combo = ttk.Combobox(
        preset_row,
        textvariable=preset_var,
        values=preset_names + [PRESET_CUSTOM_LABEL],
        state="readonly",
        width=28,
    )
    preset_combo.pack(side="left", padx=(8, 0))

    scroll_controls = EffectControlGroup()
    scroll_controls.add(preset_label)
    scroll_controls.add(preset_combo, readonly=True)

    enabled_var = tk.BooleanVar(value=bool(cfg["enabled"]))
    desktop_var = tk.BooleanVar(value=bool(cfg["desktopEnabled"]))
    settle_var = tk.BooleanVar(value=bool(cfg["headingSettle"]))
    debug_var = tk.BooleanVar(value=bool(cfg["debug"]))
    mobile_var = tk.StringVar(value=str(cfg["mobileMode"]))
    reduced_var = tk.StringVar(value=str(cfg["reducedMotionMode"]))
    header_auto_var = tk.BooleanVar(value=cfg["headerOffset"] is None)

    enabled_cb = ttk.Checkbutton(pad, text="Efekt włączony (kill switch)", variable=enabled_var)
    enabled_cb.pack(anchor="w")
    desktop_cb = ttk.Checkbutton(pad, text="Aktywny na desktopie", variable=desktop_var)
    desktop_cb.pack(anchor="w")
    scroll_controls.add(desktop_cb)

    mode_row = ttk.Frame(pad)
    mode_row.pack(fill="x", pady=(6, 0))
    mobile_label = ttk.Label(mode_row, text="Tryb mobile:")
    mobile_label.pack(side="left")
    mobile_combo = ttk.Combobox(
        mode_row, textvariable=mobile_var, values=list(MOBILE_MODES), state="readonly", width=12,
    )
    mobile_combo.pack(side="left", padx=(8, 0))
    scroll_controls.add(mobile_label)
    scroll_controls.add(mobile_combo, readonly=True)

    reduced_row = ttk.Frame(pad)
    reduced_row.pack(fill="x", pady=(4, 0))
    reduced_label = ttk.Label(reduced_row, text="Reduced motion:")
    reduced_label.pack(side="left")
    reduced_combo = ttk.Combobox(
        reduced_row, textvariable=reduced_var, values=list(REDUCED_MOTION_MODES),
        state="readonly", width=12,
    )
    reduced_combo.pack(side="left", padx=(8, 0))
    scroll_controls.add(reduced_label)
    scroll_controls.add(reduced_combo, readonly=True)

    settle_cb = ttk.Checkbutton(pad, text="Miękkie osadzenie nagłówka po zatrzymaniu", variable=settle_var)
    settle_cb.pack(anchor="w", pady=(8, 0))
    scroll_controls.add(settle_cb)

    nums = ttk.LabelFrame(pad, text="Parametry animacji", padding=(10, 8))
    nums.pack(fill="x", pady=(10, 0))
    spin_vars: dict[str, tk.StringVar] = {}

    def _spin(row: int, key: str, label: str, lo: int, hi: int, step: int) -> None:
        lbl = ttk.Label(nums, text=label)
        lbl.grid(row=row, column=0, sticky="w", pady=2)
        var = tk.StringVar(value=str(cfg[key]))
        spin_vars[key] = var
        spin = ttk.Spinbox(nums, textvariable=var, from_=lo, to=hi, increment=step, width=8)
        spin.grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
        scroll_controls.add(lbl)
        scroll_controls.add(spin)

    _spin(0, "minDuration", "Min. czas animacji (ms):", 200, 3000, 50)
    _spin(1, "maxDuration", "Maks. czas animacji (ms):", 200, 4000, 50)
    _spin(2, "wheelThreshold", "Próg gestu — kółko/trackpad (px):", 5, 400, 5)
    _spin(3, "touchThreshold", "Próg dociągania — dotyk (px):", 5, 400, 5)
    _spin(4, "headerOffsetExtra", "Zapas pod headerem (px):", 0, 200, 4)
    _spin(5, "separatorOffset", "Offset separatora w kadrze (px):", 0, 120, 2)

    motion_dynamics_var = tk.IntVar(value=int(cfg.get("motionDynamics", 50)))
    header_offset_var = tk.StringVar(value="" if cfg["headerOffset"] is None else str(cfg["headerOffset"]))
    header_row = ttk.Frame(nums)
    header_row.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
    header_auto_cb = ttk.Checkbutton(header_row, text="Offset headera: auto", variable=header_auto_var)
    header_auto_cb.pack(side="left")
    header_spin = ttk.Spinbox(
        header_row, textvariable=header_offset_var, from_=0, to=400, increment=4, width=8,
    )
    header_spin.pack(side="left", padx=(10, 0))
    scroll_controls.add(header_auto_cb)
    scroll_controls.add(header_spin)

    def _sync_header_spin() -> None:
        if not enabled_var.get():
            header_spin.configure(state="disabled")
            return
        header_spin.configure(state="disabled" if header_auto_var.get() else "normal")

    header_auto_var.trace_add("write", lambda *_a: _sync_header_spin())

    debug_cb = ttk.Checkbutton(pad, text="Debug w konsoli przeglądarki", variable=debug_var)
    debug_cb.pack(anchor="w", pady=(10, 0))
    scroll_controls.add(debug_cb)

    bind_master_toggle(enabled_var, scroll_controls, extra_sync=_sync_header_spin)

    def _apply_scroll_form(new_cfg: dict[str, Any]) -> None:
        applying_preset["active"] = True
        enabled_var.set(bool(new_cfg["enabled"]))
        desktop_var.set(bool(new_cfg["desktopEnabled"]))
        mobile_var.set(str(new_cfg["mobileMode"]))
        reduced_var.set(str(new_cfg["reducedMotionMode"]))
        settle_var.set(bool(new_cfg["headingSettle"]))
        debug_var.set(bool(new_cfg["debug"]))
        for key, var in spin_vars.items():
            var.set(str(new_cfg[key]))
        motion_dynamics_var.set(int(new_cfg.get("motionDynamics", SCROLL_DEFAULTS["motionDynamics"])))
        if new_cfg.get("headerOffset") is None:
            header_auto_var.set(True)
            header_offset_var.set("")
        else:
            header_auto_var.set(False)
            header_offset_var.set(str(new_cfg["headerOffset"]))
        _sync_header_spin()
        applying_preset["active"] = False

    def _collect_scroll() -> dict[str, Any]:
        out: dict[str, Any] = dict(SCROLL_DEFAULTS)
        out["enabled"] = bool(enabled_var.get())
        out["desktopEnabled"] = bool(desktop_var.get())
        out["mobileMode"] = mobile_var.get()
        out["reducedMotionMode"] = reduced_var.get()
        out["headingSettle"] = bool(settle_var.get())
        out["debug"] = bool(debug_var.get())
        for key, var in spin_vars.items():
            try:
                out[key] = int(float(var.get()))
            except (TypeError, ValueError):
                out[key] = SCROLL_DEFAULTS[key]
        try:
            out["motionDynamics"] = int(motion_dynamics_var.get())
        except (TypeError, ValueError):
            out["motionDynamics"] = SCROLL_DEFAULTS["motionDynamics"]
        if header_auto_var.get():
            out["headerOffset"] = None
        else:
            try:
                out["headerOffset"] = int(float(header_offset_var.get()))
            except (TypeError, ValueError):
                out["headerOffset"] = None
        return out

    _apply_scroll_form(cfg)
    preset_var.set(PRESET_CUSTOM_LABEL)

    def _on_scroll_preset(*_a: object) -> None:
        if applying_preset["active"]:
            return
        name = preset_var.get()
        if name == PRESET_CUSTOM_LABEL or name not in SCROLL_PRESETS:
            return
        _apply_scroll_form(apply_scroll_preset(name))

    preset_var.trace_add("write", _on_scroll_preset)

    ttk.Label(tab_stack, text="Scroll-over stack", font=("", 10, "bold")).pack(anchor="w")
    ttk.Label(
        tab_stack,
        text="Sekcje układają się warstwami — kolejna wjeżdża nad poprzednią przy scrollu.",
        wraplength=520,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 12))
    stack_var = tk.BooleanVar(value=stack_on)
    ttk.Checkbutton(tab_stack, text="Stack włączony dla tego wariantu", variable=stack_var).pack(anchor="w")

    def _save() -> None:
        scroll_cfg = _collect_scroll()
        errors = validate_scroll_config(scroll_cfg)
        if errors:
            messagebox.showerror(
                app_title, "Popraw przejścia:\n- " + "\n- ".join(errors), parent=dlg,
            )
            return
        try:
            saved_scroll = save_scroll_config(variant_id, scroll_cfg)
            set_variant_home_stack(variant_id, bool(stack_var.get()))
        except Exception as exc:
            messagebox.showerror(app_title, str(exc), parent=dlg)
            return
        try:
            export_home_assets(scroll_config=saved_scroll)
        except Exception as exc:
            messagebox.showerror(app_title, f"Eksport do motywu nie powiódł się:\n{exc}", parent=dlg)
            return
        status_var.set("Zapisano ustawienia przejść + assets motywu.")
        show_toast(host, "Zapisano przejścia.", duration_ms=1600)
        dlg.destroy()

    def _restore_scroll_defaults() -> None:
        _apply_scroll_form(dict(SCROLL_DEFAULTS))
        preset_var.set(preset_names[0])

    def _emergency_off() -> None:
        off = _collect_scroll()
        off["enabled"] = False
        if messagebox.askyesno(
            app_title,
            "Awaryjnie wyłączyć section-scroll?",
            parent=dlg,
        ):
            _apply_scroll_form(off)

    btn_row = ttk.Frame(dlg, padding=(12, 0, 12, 12))
    btn_row.pack(fill="x")
    ttk.Button(btn_row, text="Zamknij", command=dlg.destroy).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))
    ttk.Button(btn_row, text="Przywróć domyślne (scroll)", command=_restore_scroll_defaults).pack(side="left")
    ttk.Button(btn_row, text="Wyłącz awaryjnie", command=_emergency_off).pack(side="left", padx=(8, 0))
    if open_preview:
        ttk.Button(btn_row, text="Podgląd live", command=open_preview).pack(side="left", padx=(8, 0))

    dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)
