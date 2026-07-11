"""WS-1.2: minimalny zapis wariantu i delta-only bounded apply.

Naprawia dwa źródła niepożądanych zmian:
- zapis wariantu nie serializuje ponownie nieedytowanych pól formularza,
- Apply przenosi wyłącznie różnice wariant-base -> wariant, a nie cały stan
  wszystkich pól zarządzanych przez komponent.
"""

from __future__ import annotations

import copy
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.stronaglowna.service import path_get, path_set
from Komponenty.stronaglowna.text_html import (
    body_to_html,
    build_heading_html,
    merge_heading_body_html,
)

from . import gui_shell
from . import variants as varmod
from . import writer_safety as ws
from .config import PageEditorConfig
from .image_object_y import object_y_field_id, object_y_path
from .service_base import (
    load_template_from_path,
    load_zone_values,
    read_field,
    template_path_for_config,
    write_field,
)
from .types import TemplateField, TemplateZone, set_zone_enabled, zone_enabled


def _base_path(config: PageEditorConfig, variant_id: str) -> Path:
    return (
        config.component_dir
        / "data"
        / "variant_bases"
        / str(variant_id)
        / config.template_basename
    )


def _variant_path(config: PageEditorConfig, variant_id: str) -> Path:
    return (
        config.component_dir
        / "data"
        / "variants"
        / str(variant_id)
        / config.template_basename
    )


def _ensure_base(config: PageEditorConfig, variant_id: str, before: bytes | None) -> Path:
    if before is None:
        raise FileNotFoundError("Nie można utworzyć bazy wersji: brak pliku wariantu.")
    path = _base_path(config, variant_id)
    if not path.exists():
        ws._atomic_write(path, before)
    return path


def _norm_for_compare(field: TemplateField, value: Any) -> Any:
    if field.kind in ("bool", "blocks_visible"):
        return bool(value)
    if field.kind == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    if field.kind == "float":
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return 0.0
    if value is None:
        return ""
    return value


def _text_groups(zone: TemplateZone) -> dict[tuple[str, ...], list[TemplateField]]:
    groups: dict[tuple[str, ...], list[TemplateField]] = {}
    for field in zone.fields:
        if field.kind in ("heading", "body") and field.path:
            groups.setdefault(field.path, []).append(field)
    return groups


def _heading_tag_key(field_id: str) -> str:
    return f"_{field_id}_tag"


def _write_changed_text_group(
    template: dict[str, Any],
    path: tuple[str, ...],
    fields: list[TemplateField],
    original: dict[str, Any],
    current: dict[str, Any],
) -> bool:
    changed = False
    for field in fields:
        if current.get(field.field_id) != original.get(field.field_id):
            changed = True
        if field.kind == "heading":
            tag_key = _heading_tag_key(field.field_id)
            if current.get(tag_key) != original.get(tag_key):
                changed = True
    if not changed:
        return False

    heading_fields = [field for field in fields if field.kind == "heading"]
    body_fields = [field for field in fields if field.kind == "body"]
    if heading_fields and body_fields:
        heading = heading_fields[0]
        body = body_fields[0]
        tag = str(current.get(_heading_tag_key(heading.field_id), "h2") or "h2")
        value = merge_heading_body_html(
            str(current.get(heading.field_id, "") or ""),
            str(current.get(body.field_id, "") or ""),
            tag=tag,
        )
    elif heading_fields:
        heading = heading_fields[0]
        tag = str(current.get(_heading_tag_key(heading.field_id), "h2") or "h2")
        value = build_heading_html(
            str(current.get(heading.field_id, "") or ""),
            tag=tag,
        )
    else:
        body = body_fields[0]
        value = body_to_html(str(current.get(body.field_id, "") or ""))
    path_set(template, path, value)
    return True


def build_minimal_variant_from_state(
    config: PageEditorConfig,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Zbuduj wariant, zmieniając wyłącznie faktycznie edytowane kontrolki."""

    baseline = copy.deepcopy(
        state.get("template")
        or state.get("baseline_template")
        or {}
    )
    current_all = state.get("zone_values") or {}
    result = copy.deepcopy(baseline)

    for zone in config.zones:
        original = load_zone_values(baseline, zone)
        current = current_all.get(zone.zone_id)
        if not isinstance(current, dict):
            continue

        if bool(current.get("_enabled", True)) != bool(original.get("_enabled", True)):
            set_zone_enabled(result, zone, bool(current.get("_enabled", True)))

        for path, fields in _text_groups(zone).items():
            _write_changed_text_group(result, path, fields, original, current)

        for field in zone.fields:
            if field.kind in ("heading", "body", "theme_asset"):
                continue
            if field.field_id not in current:
                continue

            before_value = original.get(field.field_id)
            after_value = current.get(field.field_id)
            if _norm_for_compare(field, before_value) != _norm_for_compare(field, after_value):
                write_field(result, field, after_value)

            if field.kind == "shopify_image" and field.path:
                oy_key = object_y_field_id(field.field_id)
                if oy_key in current:
                    before_oy = original.get(oy_key)
                    after_oy = current.get(oy_key)
                    if before_oy != after_oy:
                        oy_path = object_y_path(field.path)
                        if oy_path:
                            path_set(result, oy_path, after_oy)

    return result


def _confirm_minimal_save(
    context: ws._EditorContext,
    pending: dict[str, Any],
) -> bool:
    baseline = context.state.get("baseline_template") or {}
    summary = gui_shell.compute_changes(context.config, baseline, pending)
    issues = gui_shell.validate_page(context.config, pending)
    errors = [issue for issue in issues if issue.level == "error"]
    warns = [issue for issue in issues if issue.level == "warn"]

    win = tk.Toplevel(context.host)
    win.title("Zapisz wersję — podsumowanie")
    position_toplevel_screen_center(win, 760, 480)
    win.transient(context.host)
    win.grab_set()

    ttk.Label(
        win,
        text=summary.headline(),
        padding=(12, 10),
        font=("", 10, "bold"),
    ).pack(anchor="w")

    detail = scrolledtext.ScrolledText(win, height=12, wrap="word", font=("", 9))
    detail.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    if summary.items:
        for item in summary.items:
            line = f"• [{item.category}] {item.zone_label} — {item.field_label}"
            if item.detail:
                line += f": {item.detail}"
            detail.insert("end", line + "\n")
    else:
        detail.insert("end", "Brak zmian.\n")

    if errors or warns:
        detail.insert("end", "\nWalidacja:\n")
        for issue in errors + warns:
            mark = "BŁĄD" if issue.level == "error" else "UWAGA"
            detail.insert("end", f"• [{mark}] {issue.zone_label}: {issue.message}\n")
    detail.insert("end", "\nMotyw: bez zmian\nAssety: bez zmian\nDeploy: nie\n")
    detail.configure(state="disabled")

    approved = {"value": False}

    def approve() -> None:
        if errors:
            messagebox.showerror(
                context.config.app_title,
                "Napraw błędy przed zapisem.",
                parent=win,
            )
            return
        if warns and not messagebox.askyesno(
            context.config.app_title,
            f"Jest {len(warns)} ostrzeżeń. Kontynuować?",
            parent=win,
        ):
            return
        approved["value"] = True
        win.destroy()

    row = ttk.Frame(win, padding=(12, 0, 12, 12))
    row.pack(fill="x")
    ttk.Button(row, text="Anuluj", command=win.destroy).pack(side="right")
    ttk.Button(row, text="Zapisz wersję", command=approve).pack(
        side="right", padx=(0, 8)
    )
    context.host.wait_window(win)
    return approved["value"]


def _run_minimal_variant_save(context: ws._EditorContext) -> None:
    variant_id = str(context.state.get("variant_id") or "")
    if not variant_id:
        messagebox.showerror(
            context.config.app_title,
            "Brak aktywnej wersji.",
            parent=context.host,
        )
        return

    pending = build_minimal_variant_from_state(context.config, context.state)
    if not _confirm_minimal_save(context, pending):
        return

    path = _variant_path(context.config, variant_id)
    before = ws._read_bytes(path)
    try:
        _ensure_base(context.config, variant_id, before)
        ws.safe_persist_editor_to_variant(
            context.config,
            variant_id,
            pending,
        )
    except Exception as exc:
        messagebox.showerror(
            context.config.app_title,
            str(exc),
            parent=context.host,
        )
        return

    context.state["template"] = pending
    context.state["baseline_template"] = copy.deepcopy(pending)
    context.state["zone_values"] = {
        zone.zone_id: load_zone_values(pending, zone)
        for zone in context.config.zones
    }
    context.state["dirty"] = False
    if context.refresh_zone_list is not None:
        context.refresh_zone_list()

    label = varmod.variant_label(context.config, variant_id)
    if context.status_var is not None:
        context.status_var.set(
            f"Zapisano wersję «{label}». Plik motywu nie został zmieniony."
        )
    ws.show_toast(context.host, f"Zapisano wersję {label}.")


def _copy_raw_path(
    target: dict[str, Any],
    source: dict[str, Any],
    path: tuple[str, ...],
) -> None:
    value = copy.deepcopy(path_get(source, path))
    path_set(target, path, value)


def _apply_delta_for_zone(
    merged: dict[str, Any],
    base: dict[str, Any],
    variant: dict[str, Any],
    zone: TemplateZone,
) -> None:
    if zone_enabled(base, zone) != zone_enabled(variant, zone):
        set_zone_enabled(merged, zone, zone_enabled(variant, zone))

    handled: set[tuple[str, ...]] = set()
    for path in _text_groups(zone):
        handled.add(path)
        if path_get(base, path) != path_get(variant, path):
            _copy_raw_path(merged, variant, path)

    for field in zone.fields:
        if field.kind in ("theme_asset", "heading", "body"):
            continue
        if field.kind == "blocks_visible":
            before = bool(read_field(base, field))
            after = bool(read_field(variant, field))
            if before != after:
                write_field(merged, field, after)
            continue
        if not field.path or field.path in handled:
            continue
        if path_get(base, field.path) != path_get(variant, field.path):
            _copy_raw_path(merged, variant, field.path)

        if field.kind == "shopify_image":
            oy_path = object_y_path(field.path)
            if oy_path and path_get(base, oy_path) != path_get(variant, oy_path):
                _copy_raw_path(merged, variant, oy_path)


def merge_variant_delta(
    config: PageEditorConfig,
    current_theme: dict[str, Any],
    base: dict[str, Any],
    variant: dict[str, Any],
) -> dict[str, Any]:
    merged = copy.deepcopy(current_theme)
    for zone in config.zones:
        _apply_delta_for_zone(merged, base, variant, zone)
    return merged


def build_delta_apply_plan(
    config: PageEditorConfig,
    variant_id: str,
    *,
    theme_path: Path | None = None,
    include_effects_asset: bool = True,
) -> ws.ApplyPlan:
    path = Path(theme_path) if theme_path is not None else template_path_for_config(config)
    before = ws._read_bytes(path)
    if before is None:
        raise FileNotFoundError(f"Brak pliku motywu: {path}")

    base_path = _base_path(config, variant_id)
    if not base_path.is_file():
        raise RuntimeError(
            "Brak bezpiecznej bazy tej wersji. "
            "Przywróć wersję z backupu lub zapisz ją ponownie po aktualizacji WS-1.2."
        )

    current_theme = load_template_from_path(path)
    base = load_template_from_path(base_path)
    variant = varmod.load_variant_data(config, variant_id)
    merged = merge_variant_delta(config, current_theme, base, variant)
    after = ws._theme_bytes(path, merged)

    outputs: list[ws.PlannedOutput] = [
        ws.PlannedOutput(
            path=path,
            before_bytes=before,
            after_bytes=after,
            before_sha256=ws._sha256_bytes(before),
            after_sha256=ws._sha256_bytes(after),
            backup_label=path.stem,
        )
    ]

    if include_effects_asset:
        sections = ws.export_section_effects_for_front(config, variant_id)
        if sections:
            effects = ws._effects_output(config, variant_id)
            if effects is not None:
                outputs.append(effects)

    changed = [output for output in outputs if output.before_bytes != output.after_bytes]
    diff_parts = [ws._diff_for_output(output) for output in changed]
    diff_text = "\n\n".join(part for part in diff_parts if part.strip())
    if not diff_text:
        diff_text = "Brak zmian względem aktualnych plików motywu."

    return ws.ApplyPlan(
        config=config,
        variant_id=str(variant_id),
        outputs=tuple(outputs),
        diff_text=diff_text,
    )


_original_apply = ws.apply_bounded_plan


def apply_delta_plan(
    plan: ws.ApplyPlan,
    *,
    confirmation: str,
) -> tuple[Path, ...]:
    paths = _original_apply(plan, confirmation=confirmation)
    variant_bytes = ws._read_bytes(_variant_path(plan.config, plan.variant_id))
    if variant_bytes is not None:
        ws._atomic_write(_base_path(plan.config, plan.variant_id), variant_bytes)
    return paths


def install_delta_only_fix() -> None:
    """Zainstaluj minimalny save i delta-only apply dla wspólnego edytora."""

    ws._run_variant_only_save = _run_minimal_variant_save
    ws.build_bounded_apply_plan = build_delta_apply_plan
    ws.apply_bounded_plan = apply_delta_plan


__all__ = [
    "build_delta_apply_plan",
    "build_minimal_variant_from_state",
    "install_delta_only_fix",
    "merge_variant_delta",
]
