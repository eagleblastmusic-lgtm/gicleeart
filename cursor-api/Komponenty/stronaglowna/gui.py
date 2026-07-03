"""GUI: Strona główna — sekcje landing page (templates/index.json)."""

from __future__ import annotations

import copy
import io
import json
import shutil
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from PIL import Image, ImageTk

from .home_features import (
    DEPLOY_TARGETS,
    compute_changes,
    diff_against_file,
    list_backups,
    preview_url,
    restore_backup,
    scan_section_keys,
    validate_homepage,
    write_home_assets,
)
import Komponenty.stronaglowna.home_features as home_features_mod
from .homepage_variants import (
    active_variant_id,
    apply_variant_to_theme,
    ensure_variants_initialized,
    list_variants,
    load_variant_into_editor,
    persist_editor_to_variant,
    set_active_variant,
    variant_label,
)
from .collage_gui import add_collage_launcher
from .video_picker import pick_shopify_video
from .registry import HOME_ZONES, SITE_NOTICE_ZONE_ID, HomeField, HomeZone, zone_by_id
from .service import (
    _boomerang_loop_is_current,
    _data_dir,
    apply_zone_values,
    backup_before_save,
    copy_mobile_hero,
    deploy_theme,
    fetch_thumbnail_bytes,
    fetch_shopify_file_bytes,
    index_template_path,
    load_index_template,
    load_theme_settings,
    load_zone_values,
    mobile_hero_path,
    build_boomerang_loop_video,
    save_index_template,
    save_theme_settings,
    shopify_cli_popen,
    shopify_ref_label,
    sync_hero_boomerang_video,
    theme_dev_http_ready,
    theme_dev_port_open,
    theme_root,
    upload_shopify_image,
    upload_shopify_video,
    validate_template_paths,
    VIDEO_SUFFIXES,
)

APP_TITLE = "Strona główna — landing page"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_THUMB_SIZE = (128, 96)


def main() -> None:
    root = TkinterDnD.Tk() if _HAS_DND else tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1280, 860)
    root.minsize(980, 640)
    _build_ui(root)
    root.mainloop()


def _heading_tag_key(field_id: str) -> str:
    return f"_{field_id}_tag"


def _parse_dnd_paths(data: str) -> list[Path]:
    out: list[Path] = []
    buf = ""
    for ch in data:
        if ch in "{}":
            continue
        if ch == " " and buf.startswith("{") and buf.endswith("}"):
            out.append(Path(buf[1:-1]))
            buf = ""
            continue
        buf += ch
    if buf:
        out.append(Path(buf.strip("{}")))
    return out


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    state: dict[str, Any] = {
        "template": {},
        "settings": {},
        "zone_values": {},
        "selected_zone_id": None,
        "dirty": False,
        "widgets": {},
        "thumb_refs": [],
        "variant_id": "home1",
        "switching_variant": False,
    }

    ensure_variants_initialized()
    state["variant_id"] = active_variant_id()

    intro = ttk.Frame(host, padding=(14, 12))
    intro.pack(fill="x")
    ttk.Label(
        intro,
        text="Zarządzanie sekcjami strony głównej sklepu.",
        font=("", 10, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        intro,
        text=(
            "Edytujesz treści i grafiki w repozytorium motywu (index.json + ustawienia site notice). "
            "Przed zapisem tworzona jest kopia zapasowa. Wdróż motyw, aby opublikować na sklepie."
        ),
        wraplength=1100,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 0))

    variant_row = ttk.Frame(intro)
    variant_row.pack(fill="x", pady=(10, 0))
    ttk.Label(variant_row, text="Wersja strony głównej:", font=("", 9, "bold")).pack(side="left")
    variant_labels = [v["label"] for v in list_variants()]
    variant_by_label = {v["label"]: v["id"] for v in list_variants()}
    variant_by_id = {v["id"]: v["label"] for v in list_variants()}
    variant_var = tk.StringVar(value=variant_by_id.get(state["variant_id"], variant_labels[0]))
    variant_combo = ttk.Combobox(
        variant_row,
        textvariable=variant_var,
        values=variant_labels,
        state="readonly",
        width=28,
    )
    variant_combo.pack(side="left", padx=(8, 0))
    ttk.Label(
        variant_row,
        text="Każda wersja ma własną kopię treści. Zapis aktualizuje motyw i bieżący wariant.",
        foreground="#777",
    ).pack(side="left", padx=(12, 0))

    body = ttk.Panedwindow(host, orient="horizontal")
    body.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    left = ttk.LabelFrame(body, text="Sekcje strony głównej", padding=(8, 8))
    right = ttk.LabelFrame(body, text="Edycja sekcji", padding=(10, 10))
    body.add(left, weight=2)
    body.add(right, weight=5)

    zone_list = tk.Listbox(left, height=15, exportselection=False, activestyle="dotbox")
    zone_list.pack(fill="both", expand=True)
    for zone in HOME_ZONES:
        zone_list.insert("end", zone.label)

    status_var = tk.StringVar(value="Wczytywanie…")
    ttk.Label(left, textvariable=status_var, foreground="#666", wraplength=280).pack(anchor="w", pady=(8, 0))

    editor_host = ttk.Frame(right)
    editor_host.pack(fill="both", expand=True)
    editor_scroll = ttk.Scrollbar(editor_host, orient="vertical")
    editor_canvas = tk.Canvas(editor_host, highlightthickness=0, yscrollincrement=20)
    editor_scroll.config(command=editor_canvas.yview)
    editor_canvas.config(yscrollcommand=editor_scroll.set)
    editor_scroll.pack(side="right", fill="y")
    editor_canvas.pack(side="left", fill="both", expand=True)
    editor_inner = ttk.Frame(editor_canvas)
    editor_window = editor_canvas.create_window((0, 0), window=editor_inner, anchor="nw")

    def _on_editor_configure(_evt=None) -> None:
        editor_canvas.configure(scrollregion=editor_canvas.bbox("all"))
        editor_canvas.itemconfigure(editor_window, width=editor_canvas.winfo_width())

    editor_inner.bind("<Configure>", _on_editor_configure)
    editor_canvas.bind("<Configure>", _on_editor_configure)

    def _bind_mousewheel(evt) -> None:
        editor_canvas.yview_scroll(int(-1 * (evt.delta / 120)), "units")

    editor_canvas.bind_all("<MouseWheel>", _bind_mousewheel)

    bottom = ttk.Frame(host, padding=(12, 0, 12, 12))
    bottom.pack(fill="x")

    def _mark_dirty() -> None:
        state["dirty"] = True
        status_var.set("Masz niezapisane zmiany.")

    def _clear_editor() -> None:
        for child in editor_inner.winfo_children():
            child.destroy()
        state["widgets"].clear()
        state["thumb_refs"].clear()

    def _collect_current_zone() -> None:
        zone_id = state.get("selected_zone_id")
        if not zone_id:
            return
        zone = zone_by_id(zone_id)
        if not zone:
            return
        values: dict[str, Any] = {}
        if not zone.settings_only:
            values["_enabled"] = bool(state["widgets"].get("_enabled_var", tk.BooleanVar()).get())

        for fld in zone.fields:
            w = state["widgets"].get(fld.field_id)
            if fld.kind == "heading":
                values[fld.field_id] = w.get().strip() if hasattr(w, "get") else str(w or "")
                tag_var = state["widgets"].get(_heading_tag_key(fld.field_id))
                if tag_var is not None:
                    values[_heading_tag_key(fld.field_id)] = tag_var.get() if hasattr(tag_var, "get") else "h2"
            elif fld.kind == "body":
                values[fld.field_id] = w.get("1.0", "end-1c").strip() if w else ""
            elif fld.kind == "bool" or fld.kind == "blocks_visible":
                values[fld.field_id] = bool(w.get()) if w else False
            elif fld.kind == "int":
                try:
                    values[fld.field_id] = int(w.get()) if w else 0
                except (TypeError, ValueError):
                    values[fld.field_id] = 0
            elif fld.kind == "theme_asset":
                values[fld.field_id] = state["zone_values"].get(zone_id, {}).get(fld.field_id, "")
            elif fld.kind == "shopify_image":
                full = state["widgets"].get(f"{fld.field_id}__full")
                if isinstance(full, str) and full.startswith("shopify://"):
                    values[fld.field_id] = full
                else:
                    values[fld.field_id] = state["zone_values"].get(zone_id, {}).get(fld.field_id, "")
            elif fld.kind == "shopify_video":
                full = state["widgets"].get(f"{fld.field_id}__full")
                if isinstance(full, str) and (full.startswith("shopify://") or full.startswith("gid://")):
                    values[fld.field_id] = full
                else:
                    values[fld.field_id] = state["zone_values"].get(zone_id, {}).get(fld.field_id, "")
            elif fld.kind == "media_type":
                var = state["widgets"].get(fld.field_id)
                raw = var.get() if var is not None and hasattr(var, "get") else str(var or "image")
                lowered = str(raw).lower()
                values[fld.field_id] = lowered if lowered in ("video", "collage") else "image"
            elif fld.kind == "video_collage":
                model = state["widgets"].get("hero_video_collage")
                if isinstance(model, dict):
                    model = copy.deepcopy(model)
                    loop_w = state["widgets"].get("hero_collage_loop")
                    if loop_w is not None and hasattr(loop_w, "get"):
                        model["loop"] = bool(loop_w.get())
                    values[fld.field_id] = model
                else:
                    values[fld.field_id] = state["zone_values"].get(zone_id, {}).get(
                        fld.field_id, {"loop": True, "clips": []}
                    )
            elif fld.field_id == "sn_message" and w:
                values[fld.field_id] = w.get("1.0", "end-1c").strip()
            elif w is not None:
                values[fld.field_id] = w.get() if hasattr(w, "get") else w
            else:
                values[fld.field_id] = state["zone_values"].get(zone_id, {}).get(fld.field_id, "")

        state["zone_values"][zone_id] = values

    def _hero_boomerang_enabled(zone_id: str) -> bool:
        if zone_id != "hero":
            return False
        widget = state["widgets"].get("hero_video_boomerang")
        if hasattr(widget, "get"):
            return bool(widget.get())
        return bool(state["zone_values"].get("hero", {}).get("hero_video_boomerang"))

    def _build_pending() -> tuple[dict[str, Any], dict[str, Any]]:
        template = copy.deepcopy(state.get("template") or {})
        settings = copy.deepcopy(state.get("settings") or {})
        for zone in HOME_ZONES:
            if zone.zone_id not in state["zone_values"]:
                state["zone_values"][zone.zone_id] = load_zone_values(
                    template, zone, settings=settings,
                )
            apply_zone_values(template, zone, state["zone_values"][zone.zone_id], settings=settings)
        return template, settings

    def _refresh_zone_list() -> None:
        for i, zone in enumerate(HOME_ZONES):
            row = next((r for r in (state.get("zone_rows") or []) if r["zone_id"] == zone.zone_id), None)
            enabled = row["enabled"] if row else True
            summary = (row or {}).get("summary", "")
            if zone.zone_id == SITE_NOTICE_ZONE_ID:
                prefix = "◆ "
            else:
                prefix = "● " if enabled else "○ "
            zone_list.delete(i)
            zone_list.insert(i, f"{prefix}{zone.label}")
            zone_list.itemconfig(i, foreground="#111" if enabled else "#888")
        if state.get("selected_zone_id"):
            idx = next((i for i, z in enumerate(HOME_ZONES) if z.zone_id == state["selected_zone_id"]), None)
            if idx is not None:
                zone_list.selection_clear(0, "end")
                zone_list.selection_set(idx)
                zone_list.activate(idx)

    def _set_thumbnail(label: tk.Label, *, shopify_ref: str = "", local: Path | None = None) -> None:
        def worker() -> None:
            raw = fetch_thumbnail_bytes(shopify_ref=shopify_ref, local_path=local)

            def done() -> None:
                if raw is None:
                    label.configure(image="", text="brak\npodglądu")
                    return
                try:
                    img = Image.open(io.BytesIO(raw))
                    img.thumbnail(_THUMB_SIZE, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    state["thumb_refs"].append(photo)
                    label.configure(image=photo, text="")
                except OSError:
                    label.configure(image="", text="błąd\npodglądu")

            host.after(0, done)

        label.configure(image="", text="ładowanie…")
        threading.Thread(target=worker, daemon=True).start()

    def _add_image_row(parent: ttk.Frame, fld: HomeField, zone: HomeZone, initial: str) -> None:
        is_video = fld.kind == "shopify_video"
        allowed = VIDEO_SUFFIXES if is_video else _IMAGE_SUFFIXES
        upload_label = "Wgraj film…" if is_video else "Wgraj grafikę…"
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 12))
        ttk.Label(row, text=fld.label + ":", width=28).pack(side="left", anchor="n")

        content = ttk.Frame(row)
        content.pack(side="left", fill="x", expand=True)

        top = ttk.Frame(content)
        top.pack(fill="x")

        thumb = tk.Label(top, width=18, height=6, relief="groove", bg="#eee", anchor="center")
        thumb.pack(side="left", padx=(0, 10))

        meta = ttk.Frame(top)
        meta.pack(side="left", fill="x", expand=True)

        var = tk.StringVar(
            value=shopify_ref_label(initial)
            if fld.kind in ("shopify_image", "shopify_video")
            else (initial or "(brak)")
        )
        state["widgets"][fld.field_id] = var
        state["widgets"][f"{fld.field_id}__full"] = initial
        state["widgets"][f"{fld.field_id}__thumb"] = thumb

        ttk.Label(meta, textvariable=var, foreground="#333").pack(anchor="w")
        if fld.hint:
            ttk.Label(meta, text=fld.hint, foreground="#777", wraplength=420).pack(anchor="w", pady=(2, 4))

        def _refresh_thumb(ref: str = "") -> None:
            if fld.kind == "theme_asset":
                local = mobile_hero_path()
                _set_thumbnail(thumb, local=local if local.is_file() else None)
            else:
                full = ref or str(state["widgets"].get(f"{fld.field_id}__full") or "")
                _set_thumbnail(thumb, shopify_ref=full if full.startswith(("shopify://", "gid://")) else "")

        def _upload_path(p: Path) -> None:
            if p.suffix.lower() not in allowed:
                kinds = "MP4, WebM, MOV" if is_video else "JPG, PNG, WebP"
                messagebox.showerror(APP_TITLE, f"Dozwolone: {kinds}.", parent=host)
                return
            status_var.set(f"Wgrywam: {p.name}…")

            def worker() -> None:
                try:
                    if fld.kind == "theme_asset":
                        copy_mobile_hero(p)
                        label = p.name
                        full = label
                        local = mobile_hero_path()
                    elif is_video:
                        full = upload_shopify_video(p)
                        label = shopify_ref_label(full)
                        local = None
                        zone_vals = state["zone_values"].setdefault(zone.zone_id, {})
                        zone_vals[fld.field_id] = full
                        if _hero_boomerang_enabled(zone.zone_id):
                            tmp_dir = _data_dir() / "tmp"
                            tmp_dir.mkdir(parents=True, exist_ok=True)
                            tmp_dst = tmp_dir / f"{p.stem}_boomerang{p.suffix.lower()}"
                            build_boomerang_loop_video(p, tmp_dst)
                            loop_ref = upload_shopify_video(tmp_dst)
                            zone_vals["hero_desktop_video_reversed"] = loop_ref
                        else:
                            zone_vals["hero_desktop_video_reversed"] = ""
                    else:
                        full = upload_shopify_image(p)
                        label = shopify_ref_label(full)
                        local = None

                    def done() -> None:
                        var.set(label)
                        state["widgets"][f"{fld.field_id}__full"] = full
                        if fld.kind in ("shopify_image", "shopify_video"):
                            state["zone_values"].setdefault(zone.zone_id, {})[fld.field_id] = full
                        _mark_dirty()
                        status_var.set(f"Wgrano: {label}")
                        show_toast(host, f"Wgrano {label}")
                        if fld.kind == "theme_asset" and local and local.is_file():
                            _set_thumbnail(thumb, local=local)
                        else:
                            _refresh_thumb(full)

                    host.after(0, done)
                except Exception as exc:
                    err = str(exc)
                    host.after(
                        0,
                        lambda e=err: (
                            status_var.set(f"Błąd uploadu: {e}"),
                            messagebox.showerror(APP_TITLE, e, parent=host),
                        ),
                    )

            threading.Thread(target=worker, daemon=True).start()

        def _apply_shopify_ref(full: str) -> None:
            label = shopify_ref_label(full)
            var.set(label)
            state["widgets"][f"{fld.field_id}__full"] = full
            if fld.kind in ("shopify_image", "shopify_video"):
                state["zone_values"].setdefault(zone.zone_id, {})[fld.field_id] = full
            _mark_dirty()
            status_var.set(f"Wybrano: {label}")
            show_toast(host, f"Wybrano {label}", duration_ms=1200)
            _refresh_thumb(full)

        def _pick_from_library() -> None:
            ref = pick_shopify_video(host, title=f"Wybierz film — {fld.label}")
            if not ref:
                return
            if is_video:
                zone_vals = state["zone_values"].setdefault(zone.zone_id, {})
                zone_vals[fld.field_id] = ref
                if _hero_boomerang_enabled(zone.zone_id) and "_boomerang" not in ref.rsplit("/", 1)[-1]:
                    zone_vals.pop("hero_desktop_video_reversed", None)
            _apply_shopify_ref(ref)

        def _pick() -> None:
            if is_video:
                filetypes = [
                    ("Filmy", "*.mp4 *.webm *.mov"),
                    ("Wszystkie", "*.*"),
                ]
                title = f"Wybierz film — {fld.label}"
            else:
                filetypes = [
                    ("Obrazy", "*.jpg *.jpeg *.png *.webp"),
                    ("Wszystkie", "*.*"),
                ]
                title = f"Wybierz grafikę — {fld.label}"
            path = filedialog.askopenfilename(
                parent=host,
                title=title,
                filetypes=filetypes,
            )
            if not path:
                return
            _upload_path(Path(path))

        def _on_drop(event) -> None:
            paths = _parse_dnd_paths(getattr(event, "data", "") or "")
            if not paths:
                return
            _upload_path(paths[0])

        def _download_current() -> None:
            if fld.kind == "theme_asset":
                src = mobile_hero_path()
                if not src.is_file():
                    messagebox.showinfo(APP_TITLE, "Brak pliku mobile hero w motywie.", parent=host)
                    return
                dest = filedialog.asksaveasfilename(
                    parent=host,
                    title=f"Zapisz — {fld.label}",
                    initialfile=src.name,
                    defaultextension=src.suffix or ".webp",
                    filetypes=[("Obrazy", "*.jpg *.jpeg *.png *.webp"), ("Wszystkie", "*.*")],
                )
                if not dest:
                    return
                try:
                    shutil.copy2(src, dest)
                    status_var.set(f"Zapisano: {Path(dest).name}")
                    show_toast(host, "Grafika zapisana", duration_ms=1400)
                except OSError as exc:
                    messagebox.showerror(APP_TITLE, str(exc), parent=host)
                return

            full = str(state["widgets"].get(f"{fld.field_id}__full") or "")
            if not (full.startswith("shopify://") or full.startswith("gid://")):
                messagebox.showinfo(APP_TITLE, "Brak pliku do pobrania.", parent=host)
                return
            default_name = shopify_ref_label(full)
            if is_video:
                ext = Path(default_name).suffix or ".mp4"
                filetypes = [("Filmy", "*.mp4 *.webm *.mov"), ("Wszystkie", "*.*")]
            else:
                ext = Path(default_name).suffix or ".webp"
                filetypes = [("Obrazy", "*.jpg *.jpeg *.png *.webp"), ("Wszystkie", "*.*")]
            dest = filedialog.asksaveasfilename(
                parent=host,
                title=f"Zapisz — {fld.label}",
                initialfile=default_name,
                defaultextension=ext,
                filetypes=filetypes,
            )
            if not dest:
                return
            status_var.set(f"Pobieram: {default_name}…")

            def worker() -> None:
                try:
                    data = fetch_shopify_file_bytes(full)
                    if not data:
                        raise ValueError("Nie udało się pobrać pliku z Shopify.")
                    Path(dest).write_bytes(data)

                    def done() -> None:
                        status_var.set(f"Zapisano: {Path(dest).name}")
                        show_toast(host, "Plik zapisany", duration_ms=1400)

                    host.after(0, done)
                except Exception as exc:
                    host.after(
                        0,
                        lambda: (
                            status_var.set("Błąd pobierania."),
                            messagebox.showerror(APP_TITLE, str(exc), parent=host),
                        ),
                    )

            threading.Thread(target=worker, daemon=True, name="stronaglowna-download").start()

        btn_row = ttk.Frame(meta)
        btn_row.pack(anchor="w", pady=(4, 0))
        ttk.Button(btn_row, text=upload_label, command=_pick).pack(side="left")
        if is_video:
            ttk.Button(btn_row, text="Z listy…", command=_pick_from_library).pack(side="left", padx=(8, 0))
        if zone.zone_id == "hero" and fld.kind in ("shopify_image", "shopify_video", "theme_asset"):
            ttk.Button(btn_row, text="Pobierz…", command=_download_current).pack(side="left", padx=(8, 0))
        if _HAS_DND:
            thumb.drop_target_register(DND_FILES)
            thumb.dnd_bind("<<Drop>>", _on_drop)
            ttk.Label(
                meta,
                text="lub przeciągnij plik na miniaturę",
                foreground="#888",
            ).pack(anchor="w", pady=(2, 0))
        else:
            ttk.Label(
                meta,
                text="(drag-and-drop: pip install tkinterdnd2)",
                foreground="#888",
            ).pack(anchor="w", pady=(2, 0))
        _refresh_thumb(str(initial or ""))

    def _add_hero_media_type(parent: ttk.Frame, zone: HomeZone, values: dict[str, Any]) -> None:
        fld = next(f for f in zone.fields if f.field_id == "hero_media_type")
        initial = str(values.get("hero_media_type") or "image")
        block = ttk.Frame(parent)
        block.pack(fill="x", pady=(0, 12))
        ttk.Label(block, text=fld.label + ":", width=28).pack(side="left", anchor="n")
        col = ttk.Frame(block)
        col.pack(side="left", fill="x", expand=True)
        media_var = tk.StringVar(
            value="collage" if initial == "collage" else ("video" if initial == "video" else "image")
        )
        state["widgets"][fld.field_id] = media_var

        media_slot = ttk.Frame(parent)
        media_slot.pack(fill="x")
        image_frame = ttk.Frame(media_slot)
        video_frame = ttk.Frame(media_slot)
        collage_frame = ttk.Frame(media_slot)
        state["widgets"]["hero_desktop__frame"] = image_frame
        state["widgets"]["hero_desktop_video__frame"] = video_frame
        state["widgets"]["hero_collage__frame"] = collage_frame

        def _sync_media_rows(*_args: object) -> None:
            mode = media_var.get()
            image_frame.pack_forget()
            video_frame.pack_forget()
            collage_frame.pack_forget()
            if mode == "video":
                video_frame.pack(fill="x")
            elif mode == "collage":
                collage_frame.pack(fill="x", pady=(8, 0))
            else:
                image_frame.pack(fill="x")
            _mark_dirty()

        row = ttk.Frame(col)
        row.pack(anchor="w")
        ttk.Radiobutton(
            row, text="Grafika", value="image", variable=media_var, command=_sync_media_rows,
        ).pack(side="left")
        ttk.Radiobutton(
            row, text="Film", value="video", variable=media_var, command=_sync_media_rows,
        ).pack(side="left", padx=(12, 0))
        ttk.Radiobutton(
            row, text="Kolaż wideo", value="collage", variable=media_var, command=_sync_media_rows,
        ).pack(side="left", padx=(12, 0))
        if fld.hint:
            ttk.Label(col, text=fld.hint, foreground="#777", wraplength=520).pack(anchor="w", pady=(4, 0))

        img_fld = next(f for f in zone.fields if f.field_id == "hero_desktop")
        vid_fld = next(f for f in zone.fields if f.field_id == "hero_desktop_video")
        _add_image_row(image_frame, img_fld, zone, str(values.get("hero_desktop") or ""))
        _add_image_row(video_frame, vid_fld, zone, str(values.get("hero_desktop_video") or ""))

        boomerang_fld = next((f for f in zone.fields if f.field_id == "hero_video_boomerang"), None)
        if boomerang_fld:
            boom_row = ttk.Frame(video_frame)
            boom_row.pack(fill="x", pady=(8, 0))
            boom_var = tk.BooleanVar(value=bool(values.get("hero_video_boomerang")))
            state["widgets"][boomerang_fld.field_id] = boom_var
            ttk.Checkbutton(
                boom_row,
                text=boomerang_fld.label,
                variable=boom_var,
                command=_mark_dirty,
            ).pack(anchor="w")
            if boomerang_fld.hint:
                ttk.Label(
                    boom_row,
                    text=boomerang_fld.hint,
                    foreground="#777",
                    wraplength=520,
                ).pack(anchor="w", pady=(2, 0))

        collage_fld = next((f for f in zone.fields if f.field_id == "hero_video_collage"), None)
        if collage_fld:
            add_collage_launcher(
                collage_frame,
                host=host,
                initial=values.get("hero_video_collage"),
                state=state,
                mark_dirty=_mark_dirty,
                status_var=status_var,
                show_toast=show_toast,
            )

        _sync_media_rows()

    def _show_zone(zone: HomeZone) -> None:
        prev_id = state.get("selected_zone_id")
        if prev_id and prev_id in state["zone_values"]:
            _collect_current_zone()
        _clear_editor()
        state["selected_zone_id"] = zone.zone_id
        values = state["zone_values"].get(zone.zone_id)
        if values is None:
            values = load_zone_values(
                state["template"],
                zone,
                settings=state.get("settings"),
            )
            state["zone_values"][zone.zone_id] = values

        ttk.Label(editor_inner, text=zone.label, font=("", 11, "bold")).pack(anchor="w")
        ttk.Label(editor_inner, text=zone.description, wraplength=620, foreground="#555").pack(
            anchor="w", pady=(2, 10)
        )

        if not zone.settings_only:
            enabled_var = tk.BooleanVar(value=bool(values.get("_enabled", True)))
            state["widgets"]["_enabled_var"] = enabled_var
            ttk.Checkbutton(
                editor_inner,
                text="Sekcja widoczna na stronie głównej",
                variable=enabled_var,
                command=_mark_dirty,
            ).pack(anchor="w", pady=(0, 12))

        for fld in zone.fields:
            initial = values.get(fld.field_id, "")

            if zone.zone_id == "hero" and fld.field_id in (
                "hero_media_type",
                "hero_desktop",
                "hero_desktop_video",
                "hero_video_boomerang",
                "hero_desktop_video_reversed",
                "hero_video_collage",
            ):
                if fld.field_id == "hero_media_type":
                    _add_hero_media_type(editor_inner, zone, values)
                continue

            if fld.kind in ("shopify_image", "shopify_video", "theme_asset"):
                _add_image_row(editor_inner, fld, zone, str(initial or ""))
                continue

            block = ttk.Frame(editor_inner)
            block.pack(fill="x", pady=(0, 10))
            ttk.Label(block, text=fld.label + ":", width=28).pack(side="left", anchor="n")
            col = ttk.Frame(block)
            col.pack(side="left", fill="both", expand=True)

            if fld.kind == "heading":
                var = tk.StringVar(value=str(initial or ""))
                state["widgets"][fld.field_id] = var
                tag = str(values.get(_heading_tag_key(fld.field_id), "h2") or "h2")
                tag_var = tk.StringVar(value=tag)
                state["widgets"][_heading_tag_key(fld.field_id)] = tag_var
                ttk.Entry(col, textvariable=var, width=64).pack(anchor="w")
                tag_row = ttk.Frame(col)
                tag_row.pack(anchor="w", pady=(4, 0))
                ttk.Label(tag_row, text="Poziom:", foreground="#777").pack(side="left")
                ttk.Combobox(
                    tag_row,
                    textvariable=tag_var,
                    values=("h2", "h3"),
                    width=6,
                    state="readonly",
                ).pack(side="left", padx=(6, 0))
                var.trace_add("write", lambda *_: _mark_dirty())
                tag_var.trace_add("write", lambda *_: _mark_dirty())
            elif fld.kind == "body" or fld.field_id == "sn_message":
                height = 6 if fld.kind == "body" else 4
                txt = tk.Text(col, wrap="word", height=height, width=72, font=("", 10))
                txt.insert("1.0", str(initial or ""))
                txt.pack(fill="both", expand=True)
                txt.bind("<KeyRelease>", lambda *_: _mark_dirty())
                state["widgets"][fld.field_id] = txt
                if fld.kind == "body":
                    ttk.Label(
                        col,
                        text="Akapit = linia tekstu; pusta linia = nowy akapit.",
                        foreground="#777",
                    ).pack(anchor="w", pady=(4, 0))
            elif fld.kind == "bool" or fld.kind == "blocks_visible":
                var = tk.BooleanVar(value=bool(initial))
                state["widgets"][fld.field_id] = var
                ttk.Checkbutton(col, variable=var, command=_mark_dirty).pack(anchor="w")
                if fld.hint:
                    ttk.Label(col, text=fld.hint, foreground="#777", wraplength=520).pack(anchor="w", pady=(2, 0))
            elif fld.kind == "media_type":
                continue
            elif fld.kind == "int":
                var = tk.StringVar(value=str(initial or "0"))
                state["widgets"][fld.field_id] = var
                ttk.Spinbox(col, from_=1, to=30, textvariable=var, width=6).pack(anchor="w")
                var.trace_add("write", lambda *_: _mark_dirty())
            else:
                var = tk.StringVar(value=str(initial or ""))
                state["widgets"][fld.field_id] = var
                width = 56 if fld.kind == "link" else 40
                ttk.Entry(col, textvariable=var, width=width).pack(anchor="w", fill="x", expand=True)
                var.trace_add("write", lambda *_: _mark_dirty())
                if fld.hint:
                    ttk.Label(col, text=fld.hint, foreground="#777", wraplength=520).pack(anchor="w", pady=(2, 0))
                elif fld.kind == "link":
                    ttk.Label(col, text="np. shopify://collections/all", foreground="#777").pack(anchor="w", pady=(2, 0))

        state["dirty"] = False
        status_var.set(f"Edycja: {zone.label}")

    def _on_zone_select(_evt=None) -> None:
        sel = zone_list.curselection()
        if not sel:
            return
        zone = HOME_ZONES[int(sel[0])]
        if state.get("dirty") and state.get("selected_zone_id"):
            if not messagebox.askyesno(
                APP_TITLE,
                "Masz niezapisane zmiany. Przejść dalej bez zapisu?",
                parent=host,
            ):
                _refresh_zone_list()
                return
        _show_zone(zone)

    zone_list.bind("<<ListboxSelect>>", _on_zone_select)

    def _show_scan_report(template: dict[str, Any]) -> None:
        results = scan_section_keys(template)
        problems = [r for r in results if r.status != "ok"]
        if not problems:
            return
        lines = ["Skan index.json — sekcje motywu:", ""]
        for row in problems:
            prefix = "⚠" if row.status == "remapped" else "✗"
            lines.append(f"{prefix} {row.zone_label}")
            if row.found_key:
                lines.append(f"   Znaleziono: {row.found_key} (oczekiwano: {row.expected_key})")
            lines.append(f"   {row.hint}")
            lines.append("")
        messagebox.showwarning(APP_TITLE, "\n".join(lines).strip(), parent=host)

    def _load_variant_into_ui(variant_id: str, *, keep_zone: bool = True) -> None:
        try:
            template, settings = load_variant_into_editor(variant_id)
        except Exception as exc:
            status_var.set("Błąd wczytywania wariantu.")
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return
        prev_zone = state.get("selected_zone_id") if keep_zone else None
        state["template"] = template
        state["settings"] = settings
        state["zone_values"] = {}
        state["selected_zone_id"] = None
        state["dirty"] = False
        from .service import list_zones

        state["zone_rows"] = list_zones(template, settings=settings)
        missing = validate_template_paths(template)
        scan_note = ""
        scan_rows = scan_section_keys(template)
        if any(r.status != "ok" for r in scan_rows):
            scan_note = " · sprawdź skan sekcji"
            host.after(300, lambda: _show_scan_report(template))
        label = variant_label(variant_id)
        if missing:
            status_var.set(f"{label}: {len(missing)} pól nie znaleziono w index.json.{scan_note}")
        else:
            status_var.set(f"{label}: wczytano {len(HOME_ZONES)} sekcji.{scan_note}")
        _refresh_zone_list()
        if prev_zone and zone_by_id(prev_zone):
            idx = next(i for i, z in enumerate(HOME_ZONES) if z.zone_id == prev_zone)
            zone_list.selection_clear(0, "end")
            zone_list.selection_set(idx)
            _show_zone(HOME_ZONES[idx])
        else:
            zone_list.selection_clear(0, "end")
            zone_list.selection_set(0)
            zone_list.event_generate("<<ListboxSelect>>")

    def _flush_current_variant(*, apply_theme: bool = False) -> None:
        _collect_current_zone()
        pending_template, pending_settings = _build_pending()
        persist_editor_to_variant(state["variant_id"], pending_template, pending_settings)
        if apply_theme:
            apply_variant_to_theme(state["variant_id"])

    def _switch_variant(new_id: str) -> None:
        if new_id == state.get("variant_id"):
            return
        if state.get("dirty"):
            ans = messagebox.askyesnocancel(
                APP_TITLE,
                f"Masz niezapisane zmiany w «{variant_label(state['variant_id'])}».\n\n"
                "Tak — zapisz do tego wariantu i przełącz.\n"
                "Nie — odrzuć zmiany i przełącz.\n"
                "Anuluj — zostań.",
                parent=host,
            )
            if ans is None:
                variant_var.set(variant_by_id.get(state["variant_id"], variant_labels[0]))
                return
            if ans:
                _flush_current_variant(apply_theme=False)
        else:
            _flush_current_variant(apply_theme=False)

        state["switching_variant"] = True
        try:
            set_active_variant(new_id)
            state["variant_id"] = new_id
            apply_variant_to_theme(new_id)
            _load_variant_into_ui(new_id, keep_zone=False)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            variant_var.set(variant_by_id.get(state["variant_id"], variant_labels[0]))
        finally:
            state["switching_variant"] = False

    def _on_variant_selected(_evt=None) -> None:
        if state.get("switching_variant"):
            return
        label = variant_var.get()
        new_id = variant_by_label.get(label)
        if not new_id:
            return
        _switch_variant(new_id)

    variant_combo.bind("<<ComboboxSelected>>", _on_variant_selected)

    def _reload(*, keep_zone: bool = True) -> None:
        _load_variant_into_ui(state["variant_id"], keep_zone=keep_zone)

    def _restore_hero_hidden_from_template() -> None:
        """Pola hero bez widgetów (np. pętla boomerang) — zawsze z wczytanego szablonu."""
        hero_zone = zone_by_id("hero")
        if not hero_zone:
            return
        from_file = load_zone_values(
            state.get("template") or {},
            hero_zone,
            settings=state.get("settings"),
        )
        hero = state["zone_values"].setdefault("hero", {})
        for key in ("hero_desktop_video_reversed", "hero_desktop_video", "hero_media_type"):
            if not str(hero.get(key) or "").strip() and str(from_file.get(key) or "").strip():
                hero[key] = from_file[key]
        if "hero_video_boomerang" not in hero:
            hero["hero_video_boomerang"] = bool(from_file.get("hero_video_boomerang"))
        if str(hero.get("hero_media_type") or "").strip().lower() != "collage":
            from_clips = (from_file.get("hero_video_collage") or {}).get("clips") or []
            hero_clips = (hero.get("hero_video_collage") or {}).get("clips") or []
            if from_clips and not hero_clips:
                hero["hero_video_collage"] = copy.deepcopy(from_file.get("hero_video_collage"))

    def _confirm_diff_and_validate(
        *,
        action_label: str,
    ) -> tuple[dict[str, Any], dict[str, Any]] | None:
        _collect_current_zone()
        _restore_hero_hidden_from_template()
        hero_vals = state["zone_values"].get("hero")
        if hero_vals and hero_vals.get("hero_video_boomerang") and hero_vals.get("hero_desktop_video"):
            forward = str(hero_vals.get("hero_desktop_video") or "")
            loop_ref = str(hero_vals.get("hero_desktop_video_reversed") or "")
            if not _boomerang_loop_is_current(forward, loop_ref):
                try:
                    status_var.set("Przygotowuję wersję cofniętą filmu (ffmpeg)…")
                    host.update_idletasks()
                    sync_hero_boomerang_video(hero_vals)
                except Exception as exc:
                    messagebox.showerror(
                        APP_TITLE,
                        f"Nie udało się przygotować wersji cofniętej filmu:\n{exc}",
                        parent=host,
                    )
                    status_var.set("Błąd przygotowania filmu cofniętego.")
                    return None
        baseline_template = state.get("template") or {}
        baseline_settings = state.get("settings") or {}
        pending_template, pending_settings = _build_pending()

        summary = compute_changes(
            baseline_template,
            baseline_settings,
            pending_template,
            pending_settings,
        )
        issues = validate_homepage(
            pending_template,
            pending_settings,
            zone_values=state.get("zone_values"),
        )
        errors = [i for i in issues if i.level == "error"]
        warns = [i for i in issues if i.level == "warn"]

        win = tk.Toplevel(host)
        win.title(f"{action_label} — podsumowanie")
        position_toplevel_screen_center(win, 760, 520)
        win.transient(host)
        win.grab_set()

        ttk.Label(win, text=summary.headline(), padding=(12, 10), font=("", 10, "bold")).pack(anchor="w")

        detail = scrolledtext.ScrolledText(win, height=8, wrap="word", font=("", 9))
        detail.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        if summary.items:
            for item in summary.items:
                line = f"• [{item.category}] {item.zone_label} — {item.field_label}"
                if item.detail:
                    line += f": {item.detail}"
                detail.insert("end", line + "\n")
        else:
            detail.insert("end", "Brak zmian względem wczytanego stanu.\n")
        if errors or warns:
            detail.insert("end", "\nWalidacja:\n")
            for issue in errors + warns:
                mark = "BŁĄD" if issue.level == "error" else "UWAGA"
                detail.insert("end", f"• [{mark}] {issue.zone_label}: {issue.message}\n")
        detail.configure(state="disabled")

        show_diff_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(win, text="Pokaż diff index.json względem ostatniego backupu", variable=show_diff_var).pack(
            anchor="w", padx=12,
        )

        diff_box = scrolledtext.ScrolledText(win, height=10, wrap="none", font=("Consolas", 8))
        diff_box.pack(fill="both", expand=True, padx=12, pady=(4, 8))
        diff_box.pack_forget()

        def _toggle_diff() -> None:
            if show_diff_var.get():
                diff_box.pack(fill="both", expand=True, padx=12, pady=(4, 8))
                pending_text = json.dumps(pending_template, ensure_ascii=False, indent=2) + "\n"
                backups = list_backups()
                backup_path = (
                    backups[0]["index_path"] if backups else index_template_path()
                )
                diff_text = diff_against_file(pending_text, backup_path, label="index.json (pending)")
                diff_box.configure(state="normal")
                diff_box.delete("1.0", "end")
                diff_box.insert("1.0", diff_text[:120000])
                diff_box.configure(state="disabled")
                win.update_idletasks()
            else:
                diff_box.pack_forget()

        show_diff_var.trace_add("write", lambda *_: _toggle_diff())

        choice: dict[str, Any] = {"ok": False}

        def _approve() -> None:
            if errors:
                messagebox.showerror(
                    APP_TITLE,
                    "Napraw błędy walidacji przed zapisem.",
                    parent=win,
                )
                return
            if warns and not messagebox.askyesno(
                APP_TITLE,
                f"Jest {len(warns)} ostrzeżeń. Kontynuować?",
                parent=win,
            ):
                return
            choice["ok"] = True
            win.destroy()

        btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Anuluj", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text=f"Kontynuuj ({action_label})", command=_approve).pack(side="right", padx=(0, 8))

        host.wait_window(win)
        if not choice["ok"]:
            return None
        return pending_template, pending_settings

    def _save_all() -> None:
        pending = _confirm_diff_and_validate(action_label="Zapisz")
        if pending is None:
            return
        pending_template, pending_settings = pending
        try:
            backups = backup_before_save()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Kopia zapasowa nie powiodła się:\n{exc}", parent=host)
            return

        try:
            save_index_template(pending_template)
            save_theme_settings(pending_settings)
            persist_editor_to_variant(state["variant_id"], pending_template, pending_settings)
            mobile_name = mobile_hero_path().name if mobile_hero_path().is_file() else None
            write_home_assets(
                pending_template,
                mobile_slide_urls=[mobile_name] if mobile_name else None,
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc), parent=host)
            return

        state["template"] = pending_template
        state["settings"] = pending_settings
        state["dirty"] = False
        from .service import list_zones

        state["zone_rows"] = list_zones(pending_template, settings=pending_settings)
        _refresh_zone_list()
        backup_note = backups[0].name if backups else "—"
        vlabel = variant_label(state["variant_id"])
        status_var.set(f"Zapisano «{vlabel}» + motyw. Kopia: …/data/backups/{backup_note}")
        show_toast(host, f"Zapisano {vlabel} i pliki motywu.")

    def _show_history() -> None:
        rows = list_backups()
        win = tk.Toplevel(host)
        win.title("Historia wersji — kopie zapasowe")
        position_toplevel_screen_center(win, 640, 420)
        win.transient(host)

        if not rows:
            ttk.Label(win, text="Brak kopii w data/backups/. Zapisz stronę główną, aby utworzyć pierwszą.", padding=16).pack()
            ttk.Button(win, text="Zamknij", command=win.destroy).pack(pady=(0, 12))
            return

        lb = tk.Listbox(win, height=14, exportselection=False)
        lb.pack(fill="both", expand=True, padx=12, pady=12)
        for row in rows:
            lb.insert("end", row["label"])

        def _restore() -> None:
            sel = lb.curselection()
            if not sel:
                return
            row = rows[int(sel[0])]
            if not messagebox.askyesno(
                APP_TITLE,
                f"Przywrócić wersję z {row['label']}?\n\n"
                "Nadpisze index.json i settings_data.json w repozytorium motywu.",
                parent=win,
            ):
                return
            try:
                restore_backup(row["timestamp"])
            except Exception as exc:
                messagebox.showerror(APP_TITLE, str(exc), parent=win)
                return
            show_toast(host, "Przywrócono kopię zapasową.")
            win.destroy()
            _reload(keep_zone=True)

        btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")
        ttk.Button(btn_row, text="Przywróć wybraną wersję", command=_restore).pack(side="right", padx=(0, 8))

    def _open_preview_live() -> None:
        webbrowser.open(preview_url(local=False))
        show_toast(host, "Otwieram podgląd live…")

    def _open_theme_dev_preview() -> None:
        preview = preview_url(local=True)
        if theme_dev_port_open() and theme_dev_http_ready(url=preview):
            webbrowser.open(preview)
            show_toast(host, "Otwieram lokalny podgląd theme dev.")
            return
        if theme_dev_port_open() and not theme_dev_http_ready(url=preview):
            if messagebox.askyesno(
                APP_TITLE,
                "Port 9292 jest zajęty, ale serwer nie odpowiada (czarny ekran / timeout).\n\n"
                "Zatrzymać stary proces i uruchomić theme dev od nowa?",
                parent=host,
            ):
                home_features_mod.restart_theme_dev_port()
            else:
                return

        status_var.set("Uruchamiam shopify theme dev…")

        win = tk.Toplevel(host)
        win.title("Theme dev — shopify theme dev")
        position_toplevel_screen_center(win, 720, 420)
        win.transient(host)
        ttk.Label(
            win,
            text="shopify theme dev --environment development  →  http://127.0.0.1:9292",
            padding=(12, 10),
        ).pack(anchor="w")
        log = scrolledtext.ScrolledText(win, height=16, wrap="word", font=("Consolas", 9))
        log.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
        btn_row.pack(fill="x")
        open_btn = ttk.Button(
            btn_row,
            text="Otwórz podgląd",
            command=lambda: webbrowser.open(preview_url(local=True)),
            state="disabled",
        )
        open_btn.pack(side="left")
        close_btn = ttk.Button(btn_row, text="Zamknij", command=win.destroy)
        close_btn.pack(side="right")

        def append(line: str) -> None:
            log.insert("end", line + "\n")
            log.see("end")

        def poll_ready(attempt: int = 0) -> None:
            preview = preview_url(local=True)
            if theme_dev_http_ready(url=preview):
                append("—" * 40)
                append("Serwer gotowy — otwieram podgląd…")
                open_btn.configure(state="normal")
                status_var.set("Theme dev działa (127.0.0.1:9292).")
                webbrowser.open(preview)
                show_toast(host, "Theme dev gotowy.")
                return
            if theme_dev_port_open() and attempt >= 8:
                append("Port 9292 otwarty, ale brak odpowiedzi HTTP — możliwy zawieszony theme dev.")
            proc = home_features_mod._theme_dev_proc
            if proc is not None and proc.poll() is not None:
                code = proc.returncode
                if code != 0:
                    msg = (
                        f"Theme dev zakończył się błędem (kod {code}).\n\n"
                        "Sprawdź log powyżej — często chodzi o zły theme ID w shopify.theme.toml."
                    )
                    append("—" * 40)
                    append(msg)
                    status_var.set("Theme dev — błąd.")
                    messagebox.showerror(APP_TITLE, msg, parent=win)
                return
            if attempt >= 90:
                append("—" * 40)
                append(
                    "Timeout — brak odpowiedzi HTTP na 127.0.0.1:9292.\n"
                    "Zamknij okno, uruchom Theme dev… ponownie (zabije stary proces na porcie)."
                )
                status_var.set("Theme dev — timeout.")
                return
            win.after(1000, lambda: poll_ready(attempt + 1))

        def worker() -> None:
            try:
                home_features_mod.start_theme_dev(on_line=append, force_restart=True)
                host.after(500, poll_ready)
            except FileNotFoundError as exc:
                host.after(0, lambda: append(str(exc)))
                host.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc), parent=win))
            except OSError as exc:
                host.after(0, lambda: append(f"BŁĄD: {exc}"))
                host.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc), parent=win))

        threading.Thread(target=worker, daemon=True).start()

    def _deploy_theme() -> None:
        pending = _confirm_diff_and_validate(action_label="Wdróż")
        if pending is None:
            return
        pending_template, pending_settings = pending

        picker = tk.Toplevel(host)
        picker.title("Wdróż motyw — wybierz cel")
        position_toplevel_screen_center(picker, 520, 280)
        picker.transient(host)
        picker.grab_set()

        target_var = tk.StringVar(value="development")
        for key, meta in DEPLOY_TARGETS.items():
            ttk.Radiobutton(
                picker,
                text=meta["label"],
                value=key,
                variable=target_var,
            ).pack(anchor="w", padx=16, pady=(8 if key == "development" else 2, 0))

        hint = ttk.Label(picker, text="", wraplength=460, foreground="#555", padding=(16, 8))
        hint.pack(anchor="w")

        def _update_hint(*_args) -> None:
            meta = DEPLOY_TARGETS.get(target_var.get(), {})
            hint.configure(text=str(meta.get("hint") or ""))

        target_var.trace_add("write", _update_hint)
        _update_hint()

        chosen: dict[str, Any] = {"go": False}

        def _start() -> None:
            key = target_var.get()
            meta = DEPLOY_TARGETS.get(key, {})
            if key == "live" and not messagebox.askyesno(
                APP_TITLE,
                "Wdróż na LIVE (opublikowany motyw)?\n\nTa operacja jest nieodwracalna z poziomu UI.",
                parent=picker,
            ):
                return
            chosen["go"] = True
            chosen["key"] = key
            chosen["meta"] = meta
            picker.destroy()

        btn_row = ttk.Frame(picker, padding=(12, 12))
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Anuluj", command=picker.destroy).pack(side="right")
        ttk.Button(btn_row, text="Wdróż", command=_start).pack(side="right", padx=(0, 8))

        host.wait_window(picker)
        if not chosen.get("go"):
            return

        meta = chosen["meta"]
        try:
            save_index_template(pending_template)
            save_theme_settings(pending_settings)
            mobile_name = mobile_hero_path().name if mobile_hero_path().is_file() else None
            write_home_assets(
                pending_template,
                mobile_slide_urls=[mobile_name] if mobile_name else None,
            )
            state["template"] = pending_template
            state["settings"] = pending_settings
            state["dirty"] = False
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Zapis przed deployem nie powiódł się:\n{exc}", parent=host)
            return

        env = str(meta.get("environment") or "development")
        allow_live = bool(meta.get("allow_live"))

        win = tk.Toplevel(host)
        win.title("Wdrożenie motywu — shopify theme push")
        position_toplevel_screen_center(win, 720, 420)
        win.transient(host)
        ttk.Label(
            win,
            text=f"shopify theme push --environment {env}" + (" --allow-live" if allow_live else ""),
            padding=(12, 10),
        ).pack(anchor="w")
        log = scrolledtext.ScrolledText(win, height=16, wrap="word", font=("Consolas", 9))
        log.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        log.configure(state="disabled")
        btn_row = ttk.Frame(win, padding=(12, 0, 12, 12))
        btn_row.pack(fill="x")
        close_btn = ttk.Button(btn_row, text="Zamknij", command=win.destroy, state="disabled")
        close_btn.pack(side="right")

        def append(line: str) -> None:
            log.configure(state="normal")
            log.insert("end", line + "\n")
            log.see("end")
            log.configure(state="disabled")

        def worker() -> None:
            try:
                code = deploy_theme(
                    environment=env,
                    allow_live=allow_live,
                    on_line=lambda ln: host.after(0, lambda l=ln: append(l)),
                )
                msg = "Motyw wdrożony pomyślnie." if code == 0 else f"Deploy zakończony kodem {code}."
            except Exception as exc:
                code = 1
                host.after(0, lambda: append(f"BŁĄD: {exc}"))
                msg = str(exc)

            def done() -> None:
                append("—" * 40)
                append(msg)
                close_btn.configure(state="normal")
                if code == 0:
                    show_toast(host, f"Motyw wdrożony ({env}).")
                else:
                    messagebox.showwarning(APP_TITLE, msg, parent=win)

            host.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    ttk.Button(bottom, text="Odśwież wariant", command=lambda: _reload()).pack(side="left")
    ttk.Button(bottom, text="Historia wersji…", command=_show_history).pack(side="left", padx=(8, 0))
    ttk.Button(bottom, text="Podgląd live", command=_open_preview_live).pack(side="left", padx=(8, 0))
    ttk.Button(bottom, text="Theme dev…", command=_open_theme_dev_preview).pack(side="left", padx=(8, 0))
    ttk.Button(bottom, text="Wdróż motyw…", command=_deploy_theme).pack(side="left", padx=(8, 0))

    right_btns = ttk.Frame(bottom)
    right_btns.pack(side="right")
    ttk.Button(right_btns, text="Zapisz", command=_save_all).pack(side="left", padx=(0, 6))
    if not inline:
        ttk.Button(right_btns, text="Zamknij", command=host.destroy).pack(side="left")

    _reload(keep_zone=False)
