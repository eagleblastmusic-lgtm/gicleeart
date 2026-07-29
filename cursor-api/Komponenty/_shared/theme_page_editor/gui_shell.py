"""GUI edytora stron menu — wspólna powłoka inline."""

from __future__ import annotations

import copy
import io
import json
import re
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
from typing import Any

from Komponenty._shared.recent_images import add_recent_image, list_recent_images
from Komponenty._shared.tkdnd_safe import parse_dnd_files, register_drop_target
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from PIL import Image, ImageTk

from .image_object_x import build_object_x_controls, object_x_field_id, object_x_path
from .image_object_y import build_object_y_controls, object_y_field_id

from .config import PageEditorConfig
from .features import (
    DEPLOY_TARGETS,
    compute_changes,
    list_backups,
    restore_backup,
    validate_page,
)
from .field_group_variants import (
    create_library_variant,
    delete_library_variant,
    load_variant_library,
    rename_library_variant,
    update_library_variant,
)
from .page_effects_dialog import open_image_effects_dialog, open_text_effects_dialog
from .page_section_effects_settings import (
    zone_has_image_effects,
    zone_has_text_effects,
    write_page_section_effects_asset,
)
from .section_background_ui import open_section_background_dialog
from .service_base import (
    apply_all_zone_values,
    apply_zone_values,
    backup_before_save,
    component_deploy_relpaths,
    deploy_theme,
    fetch_thumbnail_bytes,
    load_template,
    load_zone_values,
    merge_managed_zone_values,
    normalize_video_ref,
    preview_url,
    save_template,
    shopify_ref_label,
    upload_image,
    upload_video,
)
from Komponenty.stronaglowna.service import _parse_section_background
from .types import TemplateField, TemplateZone, zone_by_id
from . import variants as varmod

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov"}
_THUMB_SIZE = (128, 96)

def _is_widget_descendant(widget: object, ancestor: tk.Misc) -> bool:
    current = widget
    while current is not None:
        if current is ancestor:
            return True
        current = getattr(current, "master", None)
    return False


def _bind_scoped_mousewheel(
    host: tk.Misc,
    scroll_area: tk.Misc,
    canvas: tk.Canvas,
) -> None:
    """Przewija panel edycji tylko pod kursorem i odpina binding po zamknięciu widoku."""

    try:
        window = host.winfo_toplevel()
    except (AttributeError, tk.TclError):
        return

    def on_mousewheel(event: tk.Event) -> str | None:
        try:
            if not host.winfo_exists() or not scroll_area.winfo_exists() or not canvas.winfo_exists():
                return None

            target = getattr(event, "widget", None)
            if target is None or not _is_widget_descendant(target, scroll_area):
                x_root = getattr(event, "x_root", None)
                y_root = getattr(event, "y_root", None)
                if x_root is None or y_root is None:
                    return None
                target = window.winfo_containing(x_root, y_root)
                if target is None or not _is_widget_descendant(target, scroll_area):
                    return None

            # Kontrolki z własnym przewijaniem zachowują natywne zachowanie.
            if target is not canvas and isinstance(target, (tk.Text, tk.Listbox, ttk.Treeview)):
                return None

            delta = int(getattr(event, "delta", 0) or 0)
            if not delta:
                return None
            steps = int(-1 * (delta / 120))
            if steps == 0:
                steps = -1 if delta > 0 else 1
            canvas.yview_scroll(steps, "units")
            return "break"
        except (AttributeError, tk.TclError, TypeError, ValueError):
            return None

    try:
        bind_id = window.bind("<MouseWheel>", on_mousewheel, add="+")
    except (AttributeError, tk.TclError):
        return
    if not bind_id:
        return

    cleaned = False

    def cleanup(event: tk.Event | None = None) -> None:
        nonlocal cleaned
        if cleaned:
            return
        if event is not None and getattr(event, "widget", host) is not host:
            return
        cleaned = True
        try:
            window.unbind("<MouseWheel>", bind_id)
        except (AttributeError, tk.TclError):
            pass

    try:
        host.bind("<Destroy>", cleanup, add="+")
    except (AttributeError, tk.TclError):
        cleanup()


def build_page_editor(host: tk.Misc, config: PageEditorConfig, *, inline: bool = False) -> None:
    state: dict[str, Any] = {
        "template": {},
        "zone_values": {},
        "selected_zone_id": None,
        "dirty": False,
        "widgets": {},
        "thumb_refs": [],
        "variant_id": "",
        "switching_variant": False,
        "baseline_template": {},
        "open_field_groups": {},
        "selected_field_group_variants": {},
    }

    varmod.ensure_variants_initialized(config)
    state["variant_id"] = varmod.active_variant_id(config)

    intro = ttk.Frame(host, padding=(14, 12))
    intro.pack(fill="x")
    ttk.Label(intro, text=config.intro_title, font=("", 10, "bold")).pack(anchor="w")
    ttk.Label(intro, text=config.intro_body, wraplength=1100, foreground="#555").pack(anchor="w", pady=(4, 0))

    variant_row = ttk.Frame(intro)
    variant_row.pack(fill="x", pady=(10, 0))
    ttk.Label(variant_row, text="Wersja:", font=("", 9, "bold")).pack(side="left")
    _variant_rows = varmod.list_variants(config)
    state["variant_by_label"] = {v["label"]: v["id"] for v in _variant_rows}
    state["variant_by_id"] = {v["id"]: v["label"] for v in _variant_rows}
    variant_labels = [v["label"] for v in _variant_rows]
    variant_var = tk.StringVar(
        value=state["variant_by_id"].get(state["variant_id"], variant_labels[0])
    )
    variant_combo = ttk.Combobox(
        variant_row, textvariable=variant_var, values=variant_labels, state="readonly", width=28
    )
    variant_combo.pack(side="left", padx=(8, 0))
    ttk.Button(variant_row, text="Dodaj nową…", command=lambda: _add_variant()).pack(side="left", padx=(8, 0))
    ttk.Button(variant_row, text="Zmień nazwę…", command=lambda: _rename_variant()).pack(side="left", padx=(4, 0))
    for label, cmd in config.extra_toolbar:
        ttk.Button(variant_row, text=label, command=cmd).pack(side="left", padx=(8, 0))

    body = ttk.Panedwindow(host, orient="horizontal")
    body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    left = ttk.LabelFrame(body, text="Sekcje strony", padding=(8, 8))
    right = ttk.LabelFrame(body, text="Edycja sekcji", padding=(10, 10))
    body.add(left, weight=2)
    body.add(right, weight=5)

    zone_list = tk.Listbox(left, height=15, exportselection=False, activestyle="dotbox")
    zone_list.pack(fill="both", expand=True)
    editor_host = ttk.Frame(right)
    editor_host.pack(fill="both", expand=True)
    editor_scroll = ttk.Scrollbar(editor_host, orient="vertical")
    editor_canvas = tk.Canvas(editor_host, highlightthickness=0, yscrollincrement=20)
    editor_scroll.configure(command=editor_canvas.yview)
    editor_canvas.configure(yscrollcommand=editor_scroll.set)
    editor_scroll.pack(side="right", fill="y")
    editor_canvas.pack(side="left", fill="both", expand=True)
    editor_inner = ttk.Frame(editor_canvas)
    editor_window = editor_canvas.create_window((0, 0), window=editor_inner, anchor="nw")

    def _on_editor_configure(_event: tk.Event | None = None) -> None:
        editor_canvas.configure(scrollregion=editor_canvas.bbox("all"))
        editor_canvas.itemconfigure(editor_window, width=editor_canvas.winfo_width())

    editor_inner.bind("<Configure>", _on_editor_configure)
    editor_canvas.bind("<Configure>", _on_editor_configure)

    _bind_scoped_mousewheel(host, editor_host, editor_canvas)

    status_var = tk.StringVar(value="")
    ttk.Label(host, textvariable=status_var, foreground="#444", padding=(14, 0)).pack(anchor="w")
    bottom = ttk.Frame(host, padding=(12, 8))
    bottom.pack(fill="x")
    ttk.Button(bottom, text="Historia wersji…", command=lambda: _show_history()).pack(side="left")
    ttk.Button(bottom, text="Podgląd live", command=lambda: _open_preview()).pack(side="left", padx=(8, 0))
    ttk.Button(bottom, text="Wdróż motyw…", command=lambda: _deploy()).pack(side="left", padx=(8, 0))
    ttk.Button(bottom, text="Zapisz", command=lambda: _save_all()).pack(side="right")

    def _mark_dirty() -> None:
        if state.get("switching_variant"):
            return
        state["dirty"] = True

    def _load_variant(variant_id: str) -> None:
        state["switching_variant"] = True
        try:
            tpl = varmod.load_variant_into_editor(config, variant_id)
            state["template"] = tpl
            state["baseline_template"] = copy.deepcopy(tpl)
            state["zone_values"] = {
                z.zone_id: load_zone_values(tpl, z) for z in config.zones
            }
            state["variant_id"] = variant_id
            state["dirty"] = False
            _refresh_zone_list()
            if config.zones:
                zone_list.selection_clear(0, "end")
                zone_list.selection_set(0)
                state["selected_zone_id"] = config.zones[0].zone_id
                _render_zone_editor()
        finally:
            state["switching_variant"] = False

    def _refresh_zone_list() -> None:
        zone_list.delete(0, "end")
        tpl = state.get("template") or {}
        for zone in config.zones:
            enabled = load_zone_values(tpl, zone).get("_enabled", True)
            mark = "" if enabled else " [wył.]"
            zone_list.insert("end", f"{zone.label}{mark}")

    def _collect_pending_template() -> dict[str, Any]:
        tpl = copy.deepcopy(state.get("template") or {})
        for zone in config.zones:
            vals = state["zone_values"].get(zone.zone_id)
            if vals is not None:
                apply_zone_values(tpl, zone, vals)
        return tpl

    def _confirm_save(action_label: str) -> dict[str, Any] | None:
        pending = _collect_pending_template()
        summary = compute_changes(config, state.get("baseline_template") or {}, pending)
        issues = validate_page(config, pending)
        errors = [i for i in issues if i.level == "error"]
        warns = [i for i in issues if i.level == "warn"]

        win = tk.Toplevel(host)
        win.title(f"{action_label} — podsumowanie")
        position_toplevel_screen_center(win, 720, 460)
        win.transient(host)
        win.grab_set()
        ttk.Label(win, text=summary.headline(), padding=(12, 10), font=("", 10, "bold")).pack(anchor="w")
        detail = scrolledtext.ScrolledText(win, height=10, wrap="word", font=("", 9))
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
        detail.configure(state="disabled")
        choice: dict[str, bool] = {"ok": False}

        def _approve() -> None:
            if errors:
                messagebox.showerror(config.app_title, "Napraw błędy przed zapisem.", parent=win)
                return
            if warns and not messagebox.askyesno(config.app_title, f"Jest {len(warns)} ostrzeżeń. Kontynuować?", parent=win):
                return
            choice["ok"] = True
            win.destroy()

        btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Anuluj", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text=f"Kontynuuj ({action_label})", command=_approve).pack(side="right", padx=(0, 8))
        host.wait_window(win)
        return pending if choice["ok"] else None

    def _save_all() -> None:
        pending = _confirm_save("Zapisz")
        if pending is None:
            return
        try:
            backup_before_save(config)
        except Exception as exc:
            messagebox.showerror(config.app_title, f"Kopia zapasowa nie powiodła się:\n{exc}", parent=host)
            return
        try:
            current_template = load_template(config)
            merged_template = merge_managed_zone_values(config, current_template, pending)
            save_template(config, merged_template)
            varmod.persist_editor_to_variant(config, state["variant_id"], pending)
            if config.after_template_save:
                config.after_template_save()
        except Exception as exc:
            messagebox.showerror(config.app_title, str(exc), parent=host)
            return
        if config.section_effects_asset_enabled:
            try:
                write_page_section_effects_asset(config, state["variant_id"])
            except OSError:
                pass
        state["template"] = pending
        state["baseline_template"] = copy.deepcopy(pending)
        state["dirty"] = False
        _refresh_zone_list()
        vlabel = varmod.variant_label(config, state["variant_id"])
        status_var.set(f"Zapisano «{vlabel}» + motyw ({config.template_basename}).")
        show_toast(host, f"Zapisano {vlabel}.")

    def _show_history() -> None:
        rows = list_backups(config)
        win = tk.Toplevel(host)
        win.title("Historia wersji")
        position_toplevel_screen_center(win, 560, 380)
        win.transient(host)
        if not rows:
            ttk.Label(win, text="Brak kopii. Zapisz stronę, aby utworzyć pierwszą.", padding=16).pack()
            ttk.Button(win, text="Zamknij", command=win.destroy).pack(pady=(0, 12))
            return
        lb = tk.Listbox(win, height=12)
        lb.pack(fill="both", expand=True, padx=12, pady=12)
        for row in rows:
            lb.insert("end", row["name"])

        def _do_restore() -> None:
            sel = lb.curselection()
            if not sel:
                return
            path = Path(rows[int(sel[0])]["path"])
            if not messagebox.askyesno(config.app_title, f"Przywrócić kopię {path.name}?", parent=win):
                return
            try:
                restore_backup(config, path)
                tpl = varmod.load_variant_into_editor(config, state["variant_id"])
                state["template"] = tpl
                state["baseline_template"] = copy.deepcopy(tpl)
                state["zone_values"] = {z.zone_id: load_zone_values(tpl, z) for z in config.zones}
                _refresh_zone_list()
                _render_zone_editor()
                status_var.set(f"Przywrócono z kopii: {path.name}")
                show_toast(host, "Przywrócono kopię zapasową.")
                win.destroy()
            except Exception as exc:
                messagebox.showerror(config.app_title, str(exc), parent=win)

        ttk.Button(win, text="Przywróć", command=_do_restore).pack(side="left", padx=12, pady=(0, 12))
        ttk.Button(win, text="Zamknij", command=win.destroy).pack(side="right", padx=12, pady=(0, 12))

    def _open_preview() -> None:
        webbrowser.open(preview_url(config))

    def _deploy() -> None:
        pending = _confirm_save("Wdróż")
        if pending is None:
            return
        try:
            backup_before_save(config)
            current_template = load_template(config)
            merged_template = merge_managed_zone_values(config, current_template, pending)
            save_template(config, merged_template)
            varmod.persist_editor_to_variant(config, state["variant_id"], pending)
            if config.after_template_save:
                config.after_template_save()
            state["template"] = pending
            state["baseline_template"] = copy.deepcopy(pending)
        except Exception as exc:
            messagebox.showerror(config.app_title, str(exc), parent=host)
            return

        picker = tk.Toplevel(host)
        picker.title("Wdróż motyw")
        position_toplevel_screen_center(picker, 520, 280)
        picker.transient(host)
        picker.grab_set()
        target_var = tk.StringVar(value="development")
        for key, meta in DEPLOY_TARGETS.items():
            ttk.Radiobutton(
                picker, text=str(meta.get("label", key)), value=key, variable=target_var
            ).pack(anchor="w", padx=16, pady=4)
        log_box = scrolledtext.ScrolledText(picker, height=8, font=("Consolas", 8))
        log_box.pack(fill="both", expand=True, padx=12, pady=8)

        def _start() -> None:
            key = target_var.get()
            meta = DEPLOY_TARGETS.get(key, {})
            if key == "live" and not messagebox.askyesno(
                config.app_title, "Wdróż na LIVE?", parent=picker
            ):
                return
            log_box.insert("end", f"Deploy: {meta.get('label', key)}\n")
            log_box.update_idletasks()

            def worker() -> None:
                try:
                    if config.section_effects_asset_enabled:
                        write_page_section_effects_asset(config, state["variant_id"])
                    code = deploy_theme(
                        environment=str(meta.get("environment", key)),
                        allow_live=bool(meta.get("allow_live")),
                        only_paths=component_deploy_relpaths(config),
                        on_line=lambda line: host.after(0, lambda l=line: log_box.insert("end", l + "\n")),
                    )
                    host.after(0, lambda: status_var.set(f"Deploy zakończony (kod {code})."))
                except Exception as exc:
                    host.after(0, lambda: messagebox.showerror(config.app_title, str(exc), parent=picker))

            threading.Thread(target=worker, daemon=True).start()

        ttk.Button(picker, text="Wdróż", command=_start).pack(side="right", padx=12, pady=8)
        ttk.Button(picker, text="Zamknij", command=picker.destroy).pack(side="right", pady=8)

    def _add_variant() -> None:
        if state.get("dirty"):
            if not messagebox.askyesno(
                config.app_title, "Masz niezapisane zmiany. Kontynuować bez zapisu?", parent=host
            ):
                return
        label = simpledialog.askstring(
            config.app_title,
            "Nazwa nowej wersji:",
            initialvalue=varmod.suggest_variant_label(config, state["variant_id"]),
            parent=host,
        )
        if not label:
            return
        try:
            new_id = varmod.create_variant_copy(config, state["variant_id"], label.strip())
            varmod.set_active_variant(config, new_id)
            _rebuild_variant_combo(new_id)
            _load_variant(new_id)
            status_var.set(f"Utworzono wariant: {label}")
        except Exception as exc:
            messagebox.showerror(config.app_title, str(exc), parent=host)

    def _rename_variant() -> None:
        label = simpledialog.askstring(
            config.app_title,
            "Nowa nazwa wersji:",
            initialvalue=varmod.variant_label(config, state["variant_id"]),
            parent=host,
        )
        if not label:
            return
        try:
            varmod.rename_variant_label(config, state["variant_id"], label.strip())
            _rebuild_variant_combo(state["variant_id"])
        except Exception as exc:
            messagebox.showerror(config.app_title, str(exc), parent=host)

    def _rebuild_variant_combo(select_id: str) -> None:
        rows = varmod.list_variants(config)
        state["variant_by_label"] = {v["label"]: v["id"] for v in rows}
        state["variant_by_id"] = {v["id"]: v["label"] for v in rows}
        labels = [v["label"] for v in rows]
        variant_combo.configure(values=labels)
        variant_var.set(state["variant_by_id"].get(select_id, labels[0]))

    def _on_variant_change(*_a: object) -> None:
        if state.get("switching_variant"):
            return
        label = variant_var.get()
        vid = state["variant_by_label"].get(label)
        if not vid or vid == state.get("variant_id"):
            return
        if state.get("dirty"):
            if not messagebox.askyesno(
                config.app_title, "Masz niezapisane zmiany. Przełączyć wariant?", parent=host
            ):
                variant_var.set(state["variant_by_id"].get(state["variant_id"], label))
                return
        try:
            varmod.set_active_variant(config, vid)
            _load_variant(vid)
        except Exception as exc:
            messagebox.showerror(config.app_title, str(exc), parent=host)

    variant_var.trace_add("write", _on_variant_change)

    def _zone_value(zone_id: str, field_id: str) -> Any:
        return state["zone_values"].setdefault(zone_id, {}).get(field_id)

    def _preset_values_equal(left: Any, right: Any) -> bool:
        if isinstance(right, (int, float)) and not isinstance(right, bool):
            try:
                return abs(float(left) - float(right)) <= 1e-9
            except (TypeError, ValueError):
                return False
        return left == right

    def _matching_preset(zone: TemplateZone, values: dict[str, Any]) -> str | None:
        for preset_id, assignments in zone.preset_values:
            if all(
                _preset_values_equal(values.get(field_id), expected)
                for field_id, expected in assignments
            ):
                return preset_id
        return None

    def _queue_zone_render() -> None:
        if state.get("preset_render_pending"):
            return
        state["preset_render_pending"] = True

        def _render() -> None:
            state["preset_render_pending"] = False
            _render_zone_editor()

        host.after_idle(_render)

    def _set_zone_value(zone_id: str, field_id: str, value: Any) -> None:
        values = state["zone_values"].setdefault(zone_id, {})
        zone = zone_by_id(config.zones, zone_id)
        previous = values.get(field_id)
        is_preset_field = bool(zone and field_id == zone.preset_field_id)
        if _preset_values_equal(previous, value) and not is_preset_field:
            return
        values[field_id] = value

        dependent_choices_changed = False
        if zone:
            for dependent in zone.fields:
                if (
                    not dependent.choice_provider
                    or field_id not in dependent.choice_dependencies
                ):
                    continue
                available = dependent.choice_provider(dict(values))
                allowed = {choice_value for choice_value, _label in available}
                current = str(values.get(dependent.field_id) or "")
                if current not in allowed:
                    values[dependent.field_id] = (
                        "" if "" in allowed else next(iter(allowed), "")
                    )
                dependent_choices_changed = True

        if zone and zone.preset_field_id and zone.preset_values:
            if field_id == zone.preset_field_id:
                assignments = dict(zone.preset_values).get(str(value))
                if assignments:
                    for target_id, target_value in assignments:
                        values[target_id] = target_value
                    _queue_zone_render()
            else:
                controlled = {
                    target_id
                    for _preset_id, assignments in zone.preset_values
                    for target_id, _target_value in assignments
                }
                if field_id in controlled:
                    matched = _matching_preset(zone, values)
                    next_preset = matched or zone.custom_preset_value
                    if values.get(zone.preset_field_id) != next_preset:
                        values[zone.preset_field_id] = next_preset
                        _queue_zone_render()
        if dependent_choices_changed:
            _queue_zone_render()
        elif zone and any(
            any(controller_id == field_id for controller_id, _allowed in dependent.visible_when)
            for dependent in zone.fields
            if dependent.visible_when
        ):
            _queue_zone_render()
        _mark_dirty()

    def _render_thumb(parent: tk.Widget, ref: str) -> ttk.Label:
        lbl = ttk.Label(parent, text=shopify_ref_label(ref), width=24)
        if not ref:
            return lbl
        try:
            data = fetch_thumbnail_bytes(shopify_ref=ref)
            if data:
                img = Image.open(io.BytesIO(data))
                img.thumbnail(_THUMB_SIZE)
                photo = ImageTk.PhotoImage(img)
                state["thumb_refs"].append(photo)
                lbl.configure(image=photo, text="")
            else:
                lbl.configure(text="brak lokalnego\npodglądu")
        except Exception:
            lbl.configure(text="brak lokalnego\npodglądu")
        return lbl

    def _build_field_widget(zone: TemplateZone, fld: TemplateField, row: int) -> int:
        """Buduje widget pola. Zwraca indeks następnego wolnego wiersza gridu."""
        zid = zone.zone_id
        ttk.Label(
            editor_inner,
            text=fld.label,
            font=("", 9, "bold"),
            wraplength=520,
        ).grid(row=row, column=0, columnspan=2, sticky="nw", pady=(10, 2))
        row += 1
        if fld.hint:
            ttk.Label(editor_inner, text=fld.hint, foreground="#777", wraplength=520).grid(
                row=row, column=0, columnspan=2, sticky="nw", pady=(0, 4)
            )
            row += 1

        if fld.kind in ("heading", "body", "text", "link"):
            var = tk.StringVar(value=str(_zone_value(zid, fld.field_id) or ""))
            widget: tk.Widget
            if fld.kind in ("body", "text"):
                widget = scrolledtext.ScrolledText(editor_inner, height=4, width=60, wrap="word")
                widget.insert("1.0", var.get())
                widget.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))

                def _on_text(e: Any = None, w=widget, fid=fld.field_id) -> None:
                    _set_zone_value(zid, fid, w.get("1.0", "end-1c"))

                widget.bind("<KeyRelease>", _on_text)
            else:
                widget = ttk.Entry(editor_inner, textvariable=var, width=64)
                widget.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
                var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
            return row + 1
        elif fld.kind == "choice":
            field_choices = (
                fld.choice_provider(
                    dict(state["zone_values"].get(zid, {}))
                )
                if fld.choice_provider
                else fld.choices
            )
            value_to_label = dict(field_choices)
            label_to_value = {label: value for value, label in field_choices}
            current_value = str(_zone_value(zid, fld.field_id) or "")
            labels = tuple(label for _value, label in field_choices)
            display = value_to_label.get(current_value, "")
            if not display and labels:
                display = ""
            var = tk.StringVar(value=display)
            ttk.Combobox(
                editor_inner,
                textvariable=var,
                values=labels,
                state="readonly",
                width=48,
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))

            def _on_choice_write(
                *_a: Any,
                v: tk.StringVar = var,
                fid: str = fld.field_id,
                mapping: dict[str, str] = label_to_value,
                field_id: str = fld.field_id,
            ) -> None:
                _set_zone_value(zid, fid, mapping.get(v.get(), v.get()))
                if field_id == "under_hero_bg_mode":
                    host.after_idle(_render_zone_editor)

            var.trace_add("write", _on_choice_write)
            return row + 1
        elif fld.kind == "bool":
            var = tk.BooleanVar(value=bool(_zone_value(zid, fld.field_id)))
            ttk.Checkbutton(editor_inner, variable=var).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
            var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
            return row + 1
        elif fld.kind == "int":
            lo = int(fld.min_value) if fld.min_value is not None else 0
            hi = int(fld.max_value) if fld.max_value is not None else 9999
            try:
                initial = int(_zone_value(zid, fld.field_id) or lo)
            except (TypeError, ValueError):
                initial = lo
            initial = max(lo, min(hi, initial))
            # Suwak gdy pole ma jawny zakres (np. 0–100%); inaczej Spinbox.
            if fld.min_value is not None and fld.max_value is not None:
                row_fr = ttk.Frame(editor_inner)
                row_fr.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
                editor_inner.columnconfigure(0, weight=1)
                int_var = tk.IntVar(value=initial)
                unit = fld.unit if fld.unit is not None else ("%" if hi == 100 else "")
                label_var = tk.StringVar(value=f"{initial}{unit}")
                scale = ttk.Scale(
                    row_fr,
                    from_=lo,
                    to=hi,
                    orient="horizontal",
                    variable=int_var,
                )
                scale.pack(side="left", fill="x", expand=True, padx=(0, 10))
                ttk.Label(row_fr, textvariable=label_var, width=6).pack(side="left")

                def _on_int_scale(
                    *_a: object,
                    v: tk.IntVar = int_var,
                    lv: tk.StringVar = label_var,
                    fid: str = fld.field_id,
                    _lo: int = lo,
                    _hi: int = hi,
                    _step: int = max(1, int(fld.step or 1)),
                    _unit: str = unit,
                ) -> None:
                    try:
                        raw = float(v.get())
                    except (TypeError, ValueError):
                        raw = float(_lo)
                    n = int(round((raw - _lo) / _step) * _step + _lo)
                    n = max(_lo, min(_hi, n))
                    lv.set(f"{n}{_unit}")
                    _set_zone_value(zid, fid, n)

                int_var.trace_add("write", _on_int_scale)
                _set_zone_value(zid, fld.field_id, initial)
            else:
                var = tk.StringVar(value=str(initial))
                ttk.Spinbox(
                    editor_inner,
                    textvariable=var,
                    from_=lo,
                    to=hi,
                    increment=fld.step if fld.step is not None else 1,
                    width=10,
                ).grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=(0, 10)
                )
                var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
            return row + 1
        elif fld.kind == "float":
            lo = float(fld.min_value) if fld.min_value is not None else 0.0
            hi = float(fld.max_value) if fld.max_value is not None else 9999.0
            try:
                initial = float(_zone_value(zid, fld.field_id))
            except (TypeError, ValueError):
                initial = lo
            initial = max(lo, min(hi, initial))
            if fld.min_value is not None and fld.max_value is not None:
                row_fr = ttk.Frame(editor_inner)
                row_fr.grid(
                    row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10)
                )
                step = float(fld.step or 0.01)
                unit = fld.unit or ""
                float_var = tk.DoubleVar(value=initial)
                label_var = tk.StringVar(value=f"{initial:g}{unit}")
                ttk.Scale(
                    row_fr,
                    from_=lo,
                    to=hi,
                    orient="horizontal",
                    variable=float_var,
                ).pack(side="left", fill="x", expand=True, padx=(0, 10))
                ttk.Label(row_fr, textvariable=label_var, width=9).pack(side="left")

                def _on_float_scale(
                    *_a: object,
                    v: tk.DoubleVar = float_var,
                    lv: tk.StringVar = label_var,
                    fid: str = fld.field_id,
                    _lo: float = lo,
                    _hi: float = hi,
                    _step: float = step,
                    _unit: str = unit,
                ) -> None:
                    try:
                        raw = float(v.get())
                    except (TypeError, ValueError):
                        raw = _lo
                    value = round((raw - _lo) / _step) * _step + _lo
                    value = max(_lo, min(_hi, value))
                    value = round(value, 6)
                    lv.set(f"{value:g}{_unit}")
                    _set_zone_value(zid, fid, value)

                float_var.trace_add("write", _on_float_scale)
            else:
                var = tk.StringVar(value=str(initial))
                ttk.Entry(editor_inner, textvariable=var, width=12).grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=(0, 10)
                )
                var.trace_add(
                    "write",
                    lambda *_a, v=var, fid=fld.field_id: _set_zone_value(
                        zid, fid, v.get()
                    ),
                )
            return row + 1
        elif fld.kind in ("shopify_image", "shopify_video"):
            is_video = fld.kind == "shopify_video"
            suffixes = _VIDEO_SUFFIXES if is_video else _IMAGE_SUFFIXES
            frame = ttk.Frame(editor_inner)
            frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
            row += 1
            ref = str(_zone_value(zid, fld.field_id) or "")
            if ref:
                add_recent_image(ref)
            thumb = _render_thumb(frame, ref)
            thumb.pack(side="left")
            ref_var = tk.StringVar(value=ref)
            fid = fld.field_id

            def _apply_new_ref(new_ref: str, _fid: str = fid, _video: bool = is_video) -> None:
                new_ref = (new_ref or "").strip()
                if not new_ref:
                    return
                if _video:
                    new_ref = normalize_video_ref(new_ref)
                _set_zone_value(zid, _fid, new_ref)
                add_recent_image(new_ref)
                _render_zone_editor()

            def _upload_from_path(path: Path, _video: bool = is_video) -> None:
                try:
                    new_ref = upload_video(path) if _video else upload_image(path)
                    _apply_new_ref(new_ref)
                    show_toast(host, f"Wgrano: {shopify_ref_label(new_ref)}")
                except Exception as exc:
                    messagebox.showerror(config.app_title, str(exc), parent=host)

            def _pick_media(_video: bool = is_video) -> None:
                if _video:
                    filetypes = [("Filmy", "*.mp4 *.webm *.mov")]
                else:
                    filetypes = [("Obrazy", "*.jpg *.jpeg *.png *.webp")]
                path = filedialog.askopenfilename(parent=host, filetypes=filetypes)
                if not path:
                    return
                _upload_from_path(Path(path))

            def _on_media_drop(event: Any, _suffixes: set[str] = suffixes, _video: bool = is_video) -> None:
                data = getattr(event, "data", "") or ""
                paths = parse_dnd_files(data)
                matched = [p for p in paths if p.suffix.lower() in _suffixes]
                if not matched:
                    warn = (
                        "Upuść plik wideo (MP4, WebM, MOV)."
                        if _video
                        else "Upuść plik graficzny (JPG, PNG, WebP)."
                    )
                    messagebox.showwarning(config.app_title, warn, parent=host)
                    return
                _upload_from_path(matched[0])

            def _show_recent_menu(anchor: tk.Widget) -> None:
                recents = list_recent_images()
                popup = tk.Toplevel(host)
                popup.wm_overrideredirect(True)
                popup.configure(background="#2b2b2b", borderwidth=1, relief="solid")
                popup.wm_geometry(
                    f"+{anchor.winfo_rootx()}+{anchor.winfo_rooty() + anchor.winfo_height()}"
                )

                if not recents:
                    ttk.Label(popup, text="(brak historii)", padding=10).pack()
                    popup.after(50, lambda: popup.bind("<FocusOut>", lambda _e: popup.destroy()))
                    popup.focus_set()
                    return

                thumb_cache: dict[str, Any] = {}

                container = ttk.Frame(popup, padding=4)
                container.pack(fill="both", expand=True)
                listbox = tk.Listbox(
                    container,
                    height=min(len(recents), 12),
                    width=34,
                    activestyle="dotbox",
                    exportselection=False,
                )
                for rec_ref in recents:
                    listbox.insert("end", shopify_ref_label(rec_ref))
                listbox.grid(row=0, column=0, sticky="ns")
                scroll = ttk.Scrollbar(container, orient="vertical", command=listbox.yview)
                listbox.configure(yscrollcommand=scroll.set)
                scroll.grid(row=0, column=1, sticky="ns")

                preview = ttk.Label(
                    container,
                    text="Najedź, aby zobaczyć podgląd",
                    width=20,
                    anchor="center",
                    justify="center",
                )
                preview.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
                container.grid_columnconfigure(2, minsize=140)

                def _load_preview(idx: int) -> None:
                    if idx < 0 or idx >= len(recents):
                        return
                    ref = recents[idx]
                    if ref not in thumb_cache:
                        photo = None
                        try:
                            data = fetch_thumbnail_bytes(shopify_ref=ref)
                            if data:
                                img = Image.open(io.BytesIO(data))
                                img.thumbnail((128, 128))
                                photo = ImageTk.PhotoImage(img)
                        except Exception:
                            photo = None
                        thumb_cache[ref] = photo
                    photo = thumb_cache[ref]
                    if photo is not None:
                        preview.configure(image=photo, text="")
                        preview.image = photo  # type: ignore[attr-defined]
                    else:
                        preview.configure(image="", text="brak\npodglądu")

                def _on_motion(event: tk.Event) -> None:  # type: ignore[type-arg]
                    idx = listbox.nearest(event.y)
                    if idx != getattr(listbox, "_hover_idx", -1):
                        listbox._hover_idx = idx  # type: ignore[attr-defined]
                        listbox.selection_clear(0, "end")
                        listbox.selection_set(idx)
                        _load_preview(idx)

                def _apply_selected(_event: tk.Event | None = None) -> None:  # type: ignore[type-arg]
                    sel = listbox.curselection()
                    if sel:
                        chosen = recents[int(sel[0])]
                        popup.destroy()
                        _apply_new_ref(chosen)

                listbox.bind("<Motion>", _on_motion)
                listbox.bind("<Double-Button-1>", _apply_selected)
                listbox.bind("<Return>", _apply_selected)
                popup.bind("<Escape>", lambda _e: popup.destroy())
                popup.bind("<FocusOut>", lambda _e: popup.destroy())
                listbox.selection_set(0)
                listbox.focus_set()
                _load_preview(0)

            upload_label = "Wgraj film…" if is_video else "Wgraj…"
            ttk.Button(frame, text=upload_label, command=_pick_media).pack(side="left", padx=8)
            recent_btn = ttk.Button(frame, text="Ostatnie ▾")
            recent_btn.configure(command=lambda b=recent_btn: _show_recent_menu(b))
            recent_btn.pack(side="left", padx=(0, 8))
            delete_label = "Usuń film" if is_video else "Usuń grafikę"
            ttk.Button(
                frame,
                text=delete_label,
                command=lambda _fid=fid: (_set_zone_value(zid, _fid, ""), _render_zone_editor()),
            ).pack(side="left", padx=(0, 8))
            entry = ttk.Entry(frame, textvariable=ref_var, width=40)
            entry.pack(side="left", fill="x", expand=True)
            ref_var.trace_add(
                "write", lambda *_a, v=ref_var, _fid=fid: _set_zone_value(zid, _fid, v.get())
            )

            # Drag & drop pliku z Eksploratora (degraduje bez tkinterdnd2).
            for target in (frame, thumb, entry):
                register_drop_target(target, on_drop=_on_media_drop)

            # Kadrowanie tylko gdy jest grafika — nie zajmuje miejsca przy "(brak)"
            if not is_video and ref.strip():
                crop_host = ttk.Frame(editor_inner)
                crop_host.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10))
                if object_x_path(fld.path):
                    ox_key = object_x_field_id(fid)
                    build_object_x_controls(
                        crop_host,
                        initial=_zone_value(zid, ox_key),
                        on_change=lambda value, key=ox_key: _set_zone_value(zid, key, value),
                    )
                oy_key = object_y_field_id(fid)
                build_object_y_controls(
                    crop_host,
                    initial=_zone_value(zid, oy_key),
                    on_change=lambda value, key=oy_key: _set_zone_value(zid, key, value),
                )
                row += 1
            else:
                # odstęp pod rzędem przycisków, gdy brak suwaka
                frame.grid_configure(pady=(0, 10))
            return row
        else:
            var = tk.StringVar(value=str(_zone_value(zid, fld.field_id) or ""))
            ttk.Entry(editor_inner, textvariable=var, width=64).grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(0, 10)
            )
            var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
            return row + 1

    def _render_field_group_variant_library(
        zone: TemplateZone,
        library: Any,
        row: int,
    ) -> int:
        zid = zone.zone_id
        library_path = (
            config.component_dir / "data" / str(library.storage_filename)
        )
        controlled_ids = tuple(library.controlled_field_ids)
        variants = load_variant_library(
            library_path,
            controlled_field_ids=controlled_ids,
        )
        selection_key = (zid, library.group_id)
        selected_id = str(
            state.setdefault("selected_field_group_variants", {}).get(
                selection_key,
                "",
            )
            or ""
        )
        if (
            not selected_id
            and str(
                state["zone_values"].setdefault(zid, {}).get(
                    library.preset_field_id
                )
                or ""
            )
            == library.custom_preset_value
        ):
            current_values = state["zone_values"][zid]
            matched = next(
                (
                    item
                    for item in variants
                    if all(
                        current_values.get(field_id)
                        == item["values"].get(field_id)
                        for field_id in controlled_ids
                    )
                ),
                None,
            )
            if matched is not None:
                selected_id = str(matched["id"])
                state["selected_field_group_variants"][selection_key] = selected_id
        selected = next(
            (item for item in variants if item["id"] == selected_id),
            None,
        )
        if selected is None:
            selected_id = ""
            state["selected_field_group_variants"][selection_key] = ""

        panel = ttk.LabelFrame(
            editor_inner,
            text=str(library.label),
            padding=(8, 8),
        )
        panel.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=(12, 0),
            pady=(0, 8),
        )
        panel.columnconfigure(0, weight=1)

        id_by_label = {item["name"]: item["id"] for item in variants}
        labels = tuple(id_by_label)
        selected_label = selected["name"] if selected else ""
        variant_var = tk.StringVar(value=selected_label)
        combo = ttk.Combobox(
            panel,
            textvariable=variant_var,
            values=labels,
            state="readonly" if labels else "disabled",
            width=36,
        )
        combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(
            panel,
            text=(
                "Wybór kopiuje ustawienia do bieżącego wariantu strony."
                if labels
                else "Brak zapisanych wariantów — utwórz pierwszy."
            ),
            foreground="#666",
            wraplength=470,
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(4, 8))

        def _snapshot_values() -> dict[str, Any]:
            values = state["zone_values"].setdefault(zid, {})
            preset_id = str(values.get(library.preset_field_id) or "")
            assignments = dict(zone.preset_values).get(preset_id)
            resolved = dict(values)
            if assignments:
                resolved.update(dict(assignments))
            return {
                field_id: resolved.get(field_id)
                for field_id in controlled_ids
            }

        def _apply_variant(item: dict[str, Any]) -> None:
            values = state["zone_values"].setdefault(zid, {})
            values[library.preset_field_id] = library.custom_preset_value
            values.update(item["values"])
            state["selected_field_group_variants"][selection_key] = item["id"]
            _mark_dirty()
            status_var.set(f"Zastosowano wariant Lenis: {item['name']}")
            _render_zone_editor()

        def _select_variant(_event: tk.Event | None = None) -> None:
            variant_id = id_by_label.get(variant_var.get(), "")
            item = next(
                (row_item for row_item in variants if row_item["id"] == variant_id),
                None,
            )
            if item:
                _apply_variant(item)

        combo.bind("<<ComboboxSelected>>", _select_variant)

        def _create_variant() -> None:
            name = simpledialog.askstring(
                config.app_title,
                "Nazwa nowego wariantu Lenis:",
                parent=host,
            )
            if not name:
                return
            try:
                item = create_library_variant(
                    library_path,
                    name=name,
                    values=_snapshot_values(),
                    controlled_field_ids=controlled_ids,
                )
            except (OSError, ValueError) as exc:
                messagebox.showerror(config.app_title, str(exc), parent=host)
                return
            _apply_variant(item)
            show_toast(host, f"Utworzono wariant Lenis: {item['name']}")

        def _save_selected() -> None:
            if not selected_id:
                messagebox.showinfo(
                    config.app_title,
                    "Najpierw wybierz zapisany wariant.",
                    parent=host,
                )
                return
            try:
                item = update_library_variant(
                    library_path,
                    variant_id=selected_id,
                    values=_snapshot_values(),
                    controlled_field_ids=controlled_ids,
                )
            except (OSError, ValueError) as exc:
                messagebox.showerror(config.app_title, str(exc), parent=host)
                return
            _apply_variant(item)
            show_toast(host, f"Zapisano wariant Lenis: {item['name']}")

        def _rename_selected() -> None:
            if not selected:
                return
            name = simpledialog.askstring(
                config.app_title,
                "Nowa nazwa wariantu Lenis:",
                initialvalue=str(selected["name"]),
                parent=host,
            )
            if not name:
                return
            try:
                item = rename_library_variant(
                    library_path,
                    variant_id=selected_id,
                    name=name,
                    controlled_field_ids=controlled_ids,
                )
            except (OSError, ValueError) as exc:
                messagebox.showerror(config.app_title, str(exc), parent=host)
                return
            state["selected_field_group_variants"][selection_key] = item["id"]
            status_var.set(f"Zmieniono nazwę wariantu Lenis na: {item['name']}")
            _render_zone_editor()

        def _delete_selected() -> None:
            if not selected:
                return
            if not messagebox.askyesno(
                config.app_title,
                f"Usunąć wariant Lenis «{selected['name']}»?",
                parent=host,
            ):
                return
            try:
                delete_library_variant(
                    library_path,
                    variant_id=selected_id,
                    controlled_field_ids=controlled_ids,
                )
            except (OSError, ValueError) as exc:
                messagebox.showerror(config.app_title, str(exc), parent=host)
                return
            state["selected_field_group_variants"][selection_key] = ""
            status_var.set(f"Usunięto wariant Lenis: {selected['name']}")
            _render_zone_editor()

        buttons = ttk.Frame(panel)
        buttons.grid(row=2, column=0, columnspan=5, sticky="w")
        ttk.Button(
            buttons,
            text="Nowy wariant…",
            command=_create_variant,
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Zapisz wybrany",
            command=_save_selected,
            state="normal" if selected else "disabled",
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            buttons,
            text="Zmień nazwę…",
            command=_rename_selected,
            state="normal" if selected else "disabled",
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            buttons,
            text="Usuń",
            command=_delete_selected,
            state="normal" if selected else "disabled",
        ).pack(side="left", padx=(6, 0))
        return row + 1

    def _render_zone_editor() -> None:
        for child in editor_inner.winfo_children():
            child.destroy()
        state["widgets"].clear()
        state["thumb_refs"].clear()
        state["rendered_field_groups"] = set()
        zid = state.get("selected_zone_id")
        zone = zone_by_id(config.zones, zid) if zid else None
        if not zone:
            ttk.Label(editor_inner, text="Wybierz sekcję z listy po lewej.").pack(anchor="w")
            return
        enabled_var = tk.BooleanVar(value=bool(state["zone_values"].get(zid, {}).get("_enabled", True)))
        ttk.Checkbutton(
            editor_inner,
            text="Sekcja widoczna",
            variable=enabled_var,
            command=lambda: _set_zone_value(zid, "_enabled", enabled_var.get()),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        ttk.Label(editor_inner, text=zone.description, wraplength=520, foreground="#555").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        row = 2
        zone_builder = (config.zone_content_builders or {}).get(zone.zone_id)
        if callable(zone_builder):
            try:
                next_row = zone_builder(
                    editor_inner,
                    row=row,
                    host=host,
                    zone=zone,
                    config=config,
                    set_zone_value=_set_zone_value,
                    get_zone_value=lambda field_id, zone_id=None, _default_zid=zid: _zone_value(
                        zone_id or _default_zid, field_id
                    ),
                    mark_dirty=_mark_dirty,
                )
                if isinstance(next_row, int):
                    row = next_row
            except Exception as exc:
                ttk.Label(
                    editor_inner,
                    text=f"Nie udało się zbudować panelu sekcji: {exc}",
                    foreground="#a00",
                    wraplength=520,
                ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
                row += 1
        if zone.preset_field_id and zone.recommended_preset_value:
            ttk.Button(
                editor_inner,
                text="Przywróć zalecane ustawienia",
                command=lambda z=zone: _set_zone_value(
                    z.zone_id,
                    str(z.preset_field_id),
                    str(z.recommended_preset_value),
                ),
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
            row += 1
        under_hero_mode = ""
        if zone.zone_id == "under_hero_bg":
            under_hero_mode = str(
                state["zone_values"].get(zid, {}).get("under_hero_bg_mode") or ""
            ).strip().lower()

        def _render_section_bg_button(bg_field: Any, at_row: int) -> int:
            bg_status_var = tk.StringVar()

            def _bg_status_text() -> str:
                raw = state["zone_values"].get(zid, {}).get(bg_field.field_id, "")
                bg_val = _parse_section_background(raw)
                ref = bg_val.get("ref", "")
                if not ref:
                    return "(brak tła)"
                prefix = "film: " if bg_val.get("media") == "video" else ""
                label = shopify_ref_label(ref)
                return f"({prefix}{label})" if label != "(brak)" else "(brak tła)"

            bg_status_var.set(_bg_status_text())

            def _open_bg() -> None:
                def _get_widget(key: str) -> Any:
                    return state["widgets"].get(key)

                def _set_widget(key: str, value: Any) -> None:
                    state["widgets"][key] = value

                open_section_background_dialog(
                    host,
                    zone_label=zone.label,
                    bg_field_id=bg_field.field_id,
                    page_label=config.intro_title,
                    initial_value=state["zone_values"].get(zid, {}).get(bg_field.field_id),
                    get_widget=_get_widget,
                    set_widget=_set_widget,
                    get_zone_bg=lambda: _parse_section_background(
                        state["zone_values"].get(zid, {}).get(bg_field.field_id)
                    ),
                    set_zone_bg=lambda val: _set_zone_value(zid, bg_field.field_id, val),
                    mark_dirty=_mark_dirty,
                    app_title=config.app_title,
                    status_var=status_var,
                )
                bg_status_var.set(_bg_status_text())

            ttk.Label(editor_inner, text=bg_field.label).grid(
                row=at_row, column=0, columnspan=2, sticky="w", pady=(4, 2)
            )
            at_row += 1
            ttk.Button(editor_inner, text="Tło…", command=_open_bg).grid(
                row=at_row, column=0, sticky="w", pady=(0, 4)
            )
            ttk.Label(editor_inner, textvariable=bg_status_var, foreground="#666").grid(
                row=at_row, column=1, sticky="w", pady=(0, 4)
            )
            return at_row + 1

        bg_fld = next((f for f in zone.fields if f.kind == "section_background"), None)
        # FAQ «Tło pod hero»: przycisk grafiki po wyborze typu (w pętli pól).
        if bg_fld is not None and zone.zone_id != "under_hero_bg":
            row = _render_section_bg_button(bg_fld, row)
        has_text_fx = zone_has_text_effects(zone)
        has_image_fx = zone_has_image_effects(zone)
        if has_text_fx or has_image_fx:
            fx_row = ttk.Frame(editor_inner)
            fx_row.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
            if has_text_fx:
                ttk.Button(
                    fx_row,
                    text="Efekty tekstu…",
                    command=lambda z=zone: open_text_effects_dialog(
                        host,
                        config=config,
                        variant_id=state["variant_id"],
                        zone=z,
                        app_title=config.app_title,
                        status_var=status_var,
                    ),
                ).pack(side="left")
            if has_image_fx:
                ttk.Button(
                    fx_row,
                    text="Efekty grafiki…",
                    command=lambda z=zone: open_image_effects_dialog(
                        host,
                        config=config,
                        variant_id=state["variant_id"],
                        zone=z,
                        app_title=config.app_title,
                        status_var=status_var,
                    ),
                ).pack(side="left", padx=(8, 0) if has_text_fx else (0, 0))
            ttk.Label(
                fx_row,
                text="  reveal · hover · parallax — per sekcja editorial",
                foreground="#666",
            ).pack(side="left", padx=(8, 0))
            row += 1
        for fld in zone.fields:
            zone_values = state["zone_values"].get(zid, {})
            if fld.visible_when and not all(
                str(zone_values.get(controller_id) or "") in allowed_values
                for controller_id, allowed_values in fld.visible_when
            ):
                continue
            if fld.group_id:
                group_key = (zid, fld.group_id)
                rendered_groups = state.setdefault("rendered_field_groups", set())
                if group_key not in rendered_groups:
                    rendered_groups.add(group_key)
                    open_groups = state.setdefault("open_field_groups", {})
                    is_open = bool(
                        open_groups.get(group_key, not fld.group_collapsed)
                    )
                    accordion = ttk.Frame(editor_inner)
                    accordion.grid(
                        row=row,
                        column=0,
                        columnspan=2,
                        sticky="ew",
                        pady=(12, 6),
                    )
                    ttk.Separator(accordion, orient="horizontal").pack(
                        side="left",
                        fill="x",
                        expand=True,
                        padx=(0, 8),
                    )

                    def _toggle_group(
                        key: tuple[str, str] = group_key,
                        current: bool = is_open,
                    ) -> None:
                        state.setdefault("open_field_groups", {})[key] = not current
                        _render_zone_editor()

                    ttk.Button(
                        accordion,
                        text=(
                            ("▾ " if is_open else "▸ ")
                            + (fld.group_label or fld.group_id)
                        ),
                        command=_toggle_group,
                    ).pack(side="left")
                    ttk.Separator(accordion, orient="horizontal").pack(
                        side="left",
                        fill="x",
                        expand=True,
                        padx=(8, 0),
                    )
                    row += 1
                    if is_open:
                        variant_library = next(
                            (
                                item
                                for item in zone.field_group_variant_libraries
                                if item.group_id == fld.group_id
                            ),
                            None,
                        )
                        if variant_library is not None:
                            row = _render_field_group_variant_library(
                                zone,
                                variant_library,
                                row,
                            )
                else:
                    is_open = bool(
                        state.setdefault("open_field_groups", {}).get(
                            group_key,
                            not fld.group_collapsed,
                        )
                    )
                if not is_open:
                    continue
            if fld.kind == "section_background":
                if zone.zone_id == "under_hero_bg" and under_hero_mode == "image":
                    row = _render_section_bg_button(fld, row)
                continue
            if (
                zone.zone_id == "under_hero_bg"
                and fld.field_id == "under_hero_gradient"
                and under_hero_mode != "gradient"
            ):
                continue
            # FAQ / powtarzalne bloki: wizualny separator przed każdym „Pytanie N”
            q_match = re.fullmatch(r"q(\d+)_heading", fld.field_id)
            if q_match:
                sep = ttk.Frame(editor_inner)
                sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 6))
                ttk.Separator(sep, orient="horizontal").pack(fill="x", side="left", expand=True, padx=(0, 8))
                ttk.Label(
                    sep,
                    text=f"Wiersz {q_match.group(1)}",
                    foreground="#444",
                    font=("", 9, "bold"),
                ).pack(side="left")
                ttk.Separator(sep, orient="horizontal").pack(fill="x", side="left", expand=True, padx=(8, 0))
                row += 1
            row = _build_field_widget(zone, fld, row)

    def _on_zone_select(_event: tk.Event | None = None) -> None:
        sel = zone_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(config.zones):
            state["selected_zone_id"] = config.zones[idx].zone_id
            _render_zone_editor()

    zone_list.bind("<<ListboxSelect>>", _on_zone_select)
    host.winfo_toplevel().bind(
        "<<GicleeThemeAssetsChanged>>",
        lambda _event: _render_zone_editor(),
        add="+",
    )
    _load_variant(state["variant_id"])
    host.after_idle(_on_editor_configure)
    status_var.set(f"Wczytano {config.template_basename}.")
