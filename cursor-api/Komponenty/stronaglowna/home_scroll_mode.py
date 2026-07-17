"""Per-variant homepage scroll mode and GicleeApp selector.

The mode is stored in small per-variant metadata. Changing the selector applies only
that mode to the currently checked-out theme and regenerates homepage assets from
the live theme files. It never applies an old variant snapshot to the theme.
"""
from __future__ import annotations

import copy
import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from giclee_app.app_paths import atomic_write_text
from Komponenty._shared.toast import show_toast

from . import home_flow_gui
from . import homepage_variants
from . import prehero_integration as prehero

SCROLL_MODE_FILENAME = "home_scroll_mode.json"
SCROLL_MODE_SCHEMA = 1
SCROLL_SETTING_KEY = "home_flow_scroll_mode"
SCROLL_MODE_LENIS = "lenis"
SCROLL_MODE_NATIVE = "native"
SCROLL_MODE_LABELS = {
    SCROLL_MODE_LENIS: "Lenis — płynny",
    SCROLL_MODE_NATIVE: "Zwykły — natywny",
}
_LABEL_TO_MODE = {label: mode for mode, label in SCROLL_MODE_LABELS.items()}


def normalize_scroll_mode(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    return SCROLL_MODE_NATIVE if value == SCROLL_MODE_NATIVE else SCROLL_MODE_LENIS


def scroll_mode_path(
    variant_id: str,
    *,
    variants_root: Path | None = None,
    for_write: bool = False,
) -> Path:
    return homepage_variants.variant_file_path(
        str(variant_id),
        SCROLL_MODE_FILENAME,
        for_write=for_write,
        variants_root=variants_root,
    )


def load_scroll_mode(
    variant_id: str,
    *,
    variants_root: Path | None = None,
) -> str:
    path = scroll_mode_path(variant_id, variants_root=variants_root)
    if not path.is_file():
        return SCROLL_MODE_LENIS
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return SCROLL_MODE_LENIS
    if not isinstance(payload, dict):
        return SCROLL_MODE_LENIS
    return normalize_scroll_mode(payload.get("mode"))


def save_scroll_mode(
    variant_id: str,
    mode: Any,
    *,
    variants_root: Path | None = None,
) -> Path:
    normalized = normalize_scroll_mode(mode)
    path = scroll_mode_path(
        variant_id,
        variants_root=variants_root,
        for_write=True,
    )
    payload = {
        "schema": SCROLL_MODE_SCHEMA,
        "mode": normalized,
    }
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def apply_scroll_mode_to_settings(
    variant_id: str,
    settings: dict[str, Any],
) -> dict[str, Any]:
    current = settings.get("current")
    if not isinstance(current, dict):
        current = {}
        settings["current"] = current
    current[SCROLL_SETTING_KEY] = load_scroll_mode(variant_id)
    return settings


def apply_scroll_mode_to_live_theme(variant_id: str, mode: Any) -> str:
    """Apply only the scroll mode to live worktree files.

    The current ``templates/index.json`` and ``config/settings_data.json`` remain the
    source of truth. No stored homepage variant is loaded or copied over them.
    """
    from .final_difference_settings import load_final_difference_config
    from .home_features import write_home_assets
    from .scroll_settings import load_scroll_config
    from .section_bg_effects_settings import load_section_bg_effects_config
    from .service import (
        load_index_template,
        load_theme_settings,
        mobile_hero_path,
        save_theme_settings,
    )
    from .studio_reveal_settings import load_studio_reveal_config

    selected = normalize_scroll_mode(mode)
    previous_settings = load_theme_settings()
    live_settings = copy.deepcopy(previous_settings)
    current = live_settings.get("current")
    if not isinstance(current, dict):
        current = {}
        live_settings["current"] = current
    current[SCROLL_SETTING_KEY] = selected

    # The generator reads the just-written live settings when exporting pre-Hero config.
    # Roll back settings if regeneration fails, so the worktree is never left half-applied.
    save_theme_settings(live_settings)
    try:
        template = load_index_template()
        mobile_name = mobile_hero_path().name if mobile_hero_path().is_file() else None
        write_home_assets(
            template,
            mobile_slide_urls=[mobile_name] if mobile_name else None,
            stack_enabled=homepage_variants.variant_uses_home_stack(variant_id),
            scroll_config=load_scroll_config(variant_id),
            final_difference_config=load_final_difference_config(variant_id),
            studio_reveal_config=load_studio_reveal_config(variant_id),
            section_bg_effects_config=load_section_bg_effects_config(variant_id),
        )
    except Exception:
        save_theme_settings(previous_settings)
        raise

    save_scroll_mode(variant_id, selected)
    return selected


def _install_variant_bridge() -> None:
    current_load = homepage_variants.load_variant_data
    if not getattr(current_load, "_giclee_scroll_mode_bridge", False):

        def load_variant_data_with_scroll_mode(
            variant_id: str,
        ) -> tuple[dict[str, Any], dict[str, Any]]:
            template, settings = current_load(variant_id)
            return template, apply_scroll_mode_to_settings(variant_id, settings)

        setattr(load_variant_data_with_scroll_mode, "_giclee_scroll_mode_bridge", True)
        setattr(load_variant_data_with_scroll_mode, "__wrapped__", current_load)
        homepage_variants.load_variant_data = load_variant_data_with_scroll_mode

    current_persist = homepage_variants.persist_editor_to_variant
    if not getattr(current_persist, "_giclee_scroll_mode_bridge", False):

        def persist_with_scroll_mode(
            variant_id: str,
            template: dict[str, Any],
            settings: dict[str, Any],
        ) -> None:
            merged_settings = apply_scroll_mode_to_settings(
                variant_id,
                copy.deepcopy(settings),
            )
            current_persist(variant_id, template, merged_settings)

        setattr(persist_with_scroll_mode, "_giclee_scroll_mode_bridge", True)
        setattr(persist_with_scroll_mode, "__wrapped__", current_persist)
        homepage_variants.persist_editor_to_variant = persist_with_scroll_mode


def _install_export_bridge() -> None:
    current = prehero.export_prehero_config
    if getattr(current, "_giclee_scroll_mode_export", False):
        return

    def export_with_scroll_mode(settings: dict[str, Any] | None) -> dict[str, Any]:
        config = current(settings)
        source = prehero._settings_current(settings)
        config["smoothScrollMode"] = normalize_scroll_mode(
            source.get(SCROLL_SETTING_KEY)
        )
        return config

    setattr(export_with_scroll_mode, "_giclee_scroll_mode_export", True)
    setattr(export_with_scroll_mode, "__wrapped__", current)
    prehero.export_prehero_config = export_with_scroll_mode


def _install_gui_decorator() -> None:
    current = home_flow_gui._decorate_home_editor
    if getattr(current, "_giclee_scroll_mode_gui", False):
        return

    def decorate_with_scroll_mode(host: tk.Misc) -> None:
        current(host)
        if getattr(host, "_giclee_scroll_mode_decorated", False):
            return

        row = home_flow_gui._find_variant_row(host)
        if row is None:
            return

        host._giclee_scroll_mode_decorated = True  # type: ignore[attr-defined]
        mode_var = tk.StringVar()
        label_widget = ttk.Label(row, text="Scroll:", font=("", 9, "bold"))
        combo = ttk.Combobox(
            row,
            textvariable=mode_var,
            values=tuple(SCROLL_MODE_LABELS.values()),
            state="readonly",
            width=20,
        )

        hint_widget = next(
            (
                child
                for child in row.winfo_children()
                if isinstance(child, ttk.Label)
                and "Każda wersja" in home_flow_gui._widget_text(child)
            ),
            None,
        )
        try:
            label_widget.pack(side="left", padx=(12, 0), before=hint_widget)
            combo.pack(side="left", padx=(6, 0), before=hint_widget)
        except tk.TclError:
            label_widget.pack(side="left", padx=(12, 0))
            combo.pack(side="left", padx=(6, 0))

        def refresh_mode() -> None:
            mode = load_scroll_mode(homepage_variants.active_variant_id())
            mode_var.set(SCROLL_MODE_LABELS[mode])

        def save_selected_mode(_event: tk.Event | None = None) -> None:
            selected = _LABEL_TO_MODE.get(mode_var.get(), SCROLL_MODE_LENIS)
            variant_id = homepage_variants.active_variant_id()
            try:
                applied = apply_scroll_mode_to_live_theme(variant_id, selected)
            except Exception as exc:
                refresh_mode()
                messagebox.showerror(
                    "GICLÉE HOME FLOW",
                    f"Nie udało się zastosować trybu scrolla:\n{exc}",
                    parent=host,
                )
                return
            label = SCROLL_MODE_LABELS[applied]
            show_toast(
                host,
                f"Zastosowano: {label}. Odśwież podgląd Theme Dev.",
                duration_ms=2600,
            )

        combo.bind("<<ComboboxSelected>>", save_selected_mode)

        variant_combo = home_flow_gui._find_variant_combo(row)
        if variant_combo is not None and variant_combo is not combo:
            variant_combo.bind(
                "<<ComboboxSelected>>",
                lambda _event=None: host.after(140, refresh_mode),
                add="+",
            )

        host._giclee_scroll_mode_combo = combo  # type: ignore[attr-defined]
        host._giclee_scroll_mode_var = mode_var  # type: ignore[attr-defined]
        refresh_mode()

    setattr(decorate_with_scroll_mode, "_giclee_scroll_mode_gui", True)
    setattr(decorate_with_scroll_mode, "__wrapped__", current)
    home_flow_gui._decorate_home_editor = decorate_with_scroll_mode


def install_home_scroll_mode() -> None:
    _install_variant_bridge()
    _install_export_bridge()
    _install_gui_decorator()
