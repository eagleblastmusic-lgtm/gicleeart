"""GUI edytora stron menu — wspólna powłoka inline."""

from __future__ import annotations

import copy
import io
import json
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

from .image_object_y import build_object_y_controls, object_y_field_id

from .config import PageEditorConfig
from .features import (
    DEPLOY_TARGETS,
    compute_changes,
    list_backups,
    restore_backup,
    validate_page,
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
    deploy_theme,
    fetch_thumbnail_bytes,
    load_zone_values,
    normalize_video_ref,
    preview_url,
    save_template,
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
            save_template(config, pending)
            varmod.persist_editor_to_variant(config, state["variant_id"], pending)
        except Exception as exc:
            messagebox.showerror(config.app_title, str(exc), parent=host)
            return
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
            save_template(config, pending)
            varmod.persist_editor_to_variant(config, state["variant_id"], pending)
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
                    write_page_section_effects_asset(config, state["variant_id"])
                    code = deploy_theme(
                        environment=str(meta.get("environment", key)),
                        allow_live=bool(meta.get("allow_live")),
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

    def _set_zone_value(zone_id: str, field_id: str, value: Any) -> None:
        state["zone_values"].setdefault(zone_id, {})[field_id] = value
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

    def _build_field_widget(zone: TemplateZone, fld: TemplateField, row: int) -> None:
        zid = zone.zone_id
        ttk.Label(
            editor_inner,
            text=fld.label,
            font=("", 9, "bold"),
            wraplength=480,
        ).grid(row=row, column=0, sticky="nw", pady=(8, 2), padx=(0, 8))
        if fld.hint:
            ttk.Label(editor_inner, text=fld.hint, foreground="#777", wraplength=480).grid(
                row=row, column=1, sticky="w", pady=(8, 2)
            )
        row += 1

        if fld.kind in ("heading", "body", "text", "link"):
            var = tk.StringVar(value=str(_zone_value(zid, fld.field_id) or ""))
            widget: tk.Widget
            if fld.kind in ("body", "text"):
                widget = scrolledtext.ScrolledText(editor_inner, height=4, width=60, wrap="word")
                widget.insert("1.0", var.get())
                widget.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))

                def _on_text(e: Any = None, w=widget, fid=fld.field_id) -> None:
                    _set_zone_value(zid, fid, w.get("1.0", "end-1c"))

                widget.bind("<KeyRelease>", _on_text)
            else:
                widget = ttk.Entry(editor_inner, textvariable=var, width=64)
                widget.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
                var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
        elif fld.kind == "bool":
            var = tk.BooleanVar(value=bool(_zone_value(zid, fld.field_id)))
            ttk.Checkbutton(editor_inner, variable=var).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
            var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
        elif fld.kind == "int":
            var = tk.StringVar(value=str(_zone_value(zid, fld.field_id) or 0))
            ttk.Spinbox(editor_inner, textvariable=var, from_=0, to=9999, width=10).grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
            )
            var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
        elif fld.kind == "float":
            var = tk.StringVar(value=str(_zone_value(zid, fld.field_id) or 0))
            ttk.Entry(editor_inner, textvariable=var, width=12).grid(
                row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
            )
            var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))
        elif fld.kind in ("shopify_image", "shopify_video"):
            is_video = fld.kind == "shopify_video"
            suffixes = _VIDEO_SUFFIXES if is_video else _IMAGE_SUFFIXES
            frame = ttk.Frame(editor_inner)
            frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
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

            if not is_video:
                crop_host = ttk.Frame(editor_inner)
                crop_host.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
                oy_key = object_y_field_id(fid)
                build_object_y_controls(
                    crop_host,
                    initial=_zone_value(zid, oy_key),
                    on_change=lambda value, key=oy_key: _set_zone_value(zid, key, value),
                )
        else:
            var = tk.StringVar(value=str(_zone_value(zid, fld.field_id) or ""))
            ttk.Entry(editor_inner, textvariable=var, width=64).grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6)
            )
            var.trace_add("write", lambda *_a, v=var, fid=fld.field_id: _set_zone_value(zid, fid, v.get()))

    def _render_zone_editor() -> None:
        for child in editor_inner.winfo_children():
            child.destroy()
        state["widgets"].clear()
        state["thumb_refs"].clear()
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
        bg_fld = next((f for f in zone.fields if f.kind == "section_background"), None)
        if bg_fld is not None:
            bg_status_var = tk.StringVar()

            def _bg_status_text() -> str:
                raw = state["zone_values"].get(zid, {}).get(bg_fld.field_id, "")
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
                    bg_field_id=bg_fld.field_id,
                    page_label=config.intro_title,
                    initial_value=state["zone_values"].get(zid, {}).get(bg_fld.field_id),
                    get_widget=_get_widget,
                    set_widget=_set_widget,
                    get_zone_bg=lambda: _parse_section_background(
                        state["zone_values"].get(zid, {}).get(bg_fld.field_id)
                    ),
                    set_zone_bg=lambda val: _set_zone_value(zid, bg_fld.field_id, val),
                    mark_dirty=_mark_dirty,
                    app_title=config.app_title,
                    status_var=status_var,
                )
                bg_status_var.set(_bg_status_text())

            ttk.Button(editor_inner, text="Tło…", command=_open_bg).grid(
                row=row, column=0, sticky="w", pady=(0, 4)
            )
            ttk.Label(editor_inner, textvariable=bg_status_var, foreground="#666").grid(
                row=row, column=1, sticky="w", pady=(0, 4)
            )
            row += 1
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
            if fld.kind == "section_background":
                continue
            _build_field_widget(zone, fld, row)
            row += 2

    def _on_zone_select(_event: tk.Event | None = None) -> None:
        sel = zone_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < len(config.zones):
            state["selected_zone_id"] = config.zones[idx].zone_id
            _render_zone_editor()

    zone_list.bind("<<ListboxSelect>>", _on_zone_select)
    _load_variant(state["variant_id"])
    host.after_idle(_on_editor_configure)
    status_var.set(f"Wczytano {config.template_basename}.")
