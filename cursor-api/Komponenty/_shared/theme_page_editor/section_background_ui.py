"""Dialog «Tło sekcji» — grafika/film + gradient (jak Strona główna / Tło do Bio)."""

from __future__ import annotations

import io
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.theme_page_editor.image_object_y import build_object_y_controls, normalize_object_y
from Komponenty._shared.toast import show_toast
from Komponenty._shared.tkdnd_safe import parse_dnd_files, register_drop_target
from Komponenty.stronaglowna.service import (
    DEFAULT_SECTION_OVERLAY_PCT,
    _parse_section_background,
    fetch_thumbnail_bytes,
    normalize_overlay_pct,
    shopify_ref_label,
    upload_shopify_image,
    upload_shopify_video,
)
from PIL import Image, ImageTk

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_SUFFIXES = {".mp4", ".webm", ".mov"}
_THUMB_SIZE = (128, 96)


def open_section_background_dialog(
    host: tk.Misc,
    *,
    zone_label: str,
    bg_field_id: str,
    page_label: str,
    initial_value: Any,
    get_widget: Callable[[str], Any],
    set_widget: Callable[[str, Any], None],
    get_zone_bg: Callable[[], dict[str, Any]],
    set_zone_bg: Callable[[dict[str, Any]], None],
    mark_dirty: Callable[[], None],
    app_title: str,
    status_var: tk.StringVar | None = None,
) -> None:
    """Otwiera edytor tła sekcji (upload, kadrowanie, gradient, usuń tło)."""
    bg = _parse_section_background(initial_value)
    overlay_stash = normalize_overlay_pct(bg.get("overlay_pct") or DEFAULT_SECTION_OVERLAY_PCT)
    if overlay_stash <= 0:
        overlay_stash = DEFAULT_SECTION_OVERLAY_PCT
    initial_overlay = normalize_overlay_pct(bg.get("overlay_pct"))
    overlay_off_initial = initial_overlay <= 0
    thumb_refs: list[Any] = []

    dlg = tk.Toplevel(host)
    dlg.title(f"Tło — {zone_label}")
    dlg.transient(host)
    dlg.grab_set()
    dlg.geometry("580x520")
    dlg.minsize(480, 440)

    pad = ttk.Frame(dlg, padding=(14, 12))
    pad.pack(fill="both", expand=True)

    ttk.Label(pad, text=f"Tło sekcji: {zone_label}", font=("", 10, "bold")).pack(anchor="w")
    ttk.Label(
        pad,
        text=f"Grafika lub film w tle całej sekcji. Po zapisie widoczne na {page_label}.",
        wraplength=520,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 10))

    media_var = tk.StringVar(value="video" if bg.get("media") == "video" else "image")
    set_widget(f"{bg_field_id}__media", media_var)

    type_row = ttk.Frame(pad)
    type_row.pack(anchor="w", pady=(0, 10))
    ttk.Label(type_row, text="Typ:", width=8).pack(side="left")
    ttk.Radiobutton(
        type_row, text="Grafika", value="image", variable=media_var, command=lambda: _sync_bg_media()
    ).pack(side="left")
    ttk.Radiobutton(
        type_row, text="Film", value="video", variable=media_var, command=lambda: _sync_bg_media()
    ).pack(side="left", padx=(12, 0))

    body = ttk.Frame(pad)
    body.pack(fill="both", expand=True)
    image_frame = ttk.Frame(body)
    video_frame = ttk.Frame(body)

    overlay_frame = ttk.Frame(pad)
    overlay_frame.pack(fill="x", pady=(8, 0))
    overlay_off_var = tk.BooleanVar(value=overlay_off_initial)
    overlay_pct_var = tk.IntVar(value=initial_overlay if initial_overlay > 0 else overlay_stash)
    overlay_label_var = tk.StringVar(value=f"{initial_overlay}%")
    set_widget(f"{bg_field_id}__overlay_off", overlay_off_var)
    set_widget(f"{bg_field_id}__overlay_pct", overlay_pct_var)
    set_widget(f"{bg_field_id}__overlay_stash", overlay_stash)

    ttk.Label(overlay_frame, text="Przyciemnienie (gradient):").pack(anchor="w")
    overlay_controls = ttk.Frame(overlay_frame)
    overlay_controls.pack(fill="x", pady=(4, 0))
    overlay_scale = ttk.Scale(
        overlay_controls, from_=0, to=100, orient="horizontal", variable=overlay_pct_var
    )
    overlay_scale.pack(side="left", fill="x", expand=True)
    ttk.Label(overlay_controls, textvariable=overlay_label_var, width=5).pack(side="left", padx=(6, 0))

    def _effective_overlay_pct() -> int:
        if overlay_off_var.get():
            return 0
        return normalize_overlay_pct(overlay_pct_var.get())

    def _slot_key(media: str) -> str:
        return f"{bg_field_id}__{'video' if media == 'video' else 'image'}"

    def _bg_has_media() -> bool:
        media = media_var.get()
        full = str(get_widget(f"{_slot_key(media)}__full") or "")
        return full.startswith(("shopify://", "gid://"))

    def _update_overlay_label(*_args: object) -> None:
        overlay_label_var.set(f"{_effective_overlay_pct()}%")

    overlay_off_check = ttk.Checkbutton(
        overlay_frame, text="Wyłącz przyciemnienie", variable=overlay_off_var
    )
    overlay_off_check.pack(anchor="w", pady=(6, 0))

    def _set_overlay_controls_enabled(enabled: bool) -> None:
        scale_state = "normal" if enabled and not overlay_off_var.get() else "disabled"
        overlay_scale.configure(state=scale_state)
        overlay_off_check.configure(state="normal" if enabled else "disabled")

    def _persist_bg_from_widgets() -> None:
        media = media_var.get()
        slot = _slot_key(media)
        ref = str(get_widget(f"{slot}__full") or "")
        if not ref.startswith(("shopify://", "gid://")):
            media = "none"
            ref = ""
        oy_raw = get_widget(f"{bg_field_id}__object_y")
        object_y = normalize_object_y(oy_raw.get() if hasattr(oy_raw, "get") else oy_raw)
        set_zone_bg(
            {
                "media": media,
                "ref": ref,
                "overlay_pct": _effective_overlay_pct(),
                "object_y": object_y,
            }
        )

    def _on_overlay_off_change() -> None:
        if overlay_off_var.get():
            stash = normalize_overlay_pct(overlay_pct_var.get())
            if stash > 0:
                set_widget(f"{bg_field_id}__overlay_stash", stash)
            overlay_scale.configure(state="disabled")
        else:
            _set_overlay_controls_enabled(_bg_has_media())
            stash = get_widget(f"{bg_field_id}__overlay_stash") or DEFAULT_SECTION_OVERLAY_PCT
            overlay_pct_var.set(normalize_overlay_pct(stash))
        _update_overlay_label()
        _persist_bg_from_widgets()
        mark_dirty()

    overlay_off_check.configure(command=_on_overlay_off_change)

    def _on_overlay_pct_change(*_args: object) -> None:
        if not overlay_off_var.get():
            pct = normalize_overlay_pct(overlay_pct_var.get())
            if pct > 0:
                set_widget(f"{bg_field_id}__overlay_stash", pct)
        _update_overlay_label()
        _persist_bg_from_widgets()
        mark_dirty()

    overlay_pct_var.trace_add("write", _on_overlay_pct_change)

    def _set_thumb(label: tk.Label, ref: str = "") -> None:
        if not ref:
            label.configure(image="", text="brak\npodglądu")
            return

        def worker() -> None:
            raw = fetch_thumbnail_bytes(shopify_ref=ref)

            def done() -> None:
                if raw is None:
                    label.configure(image="", text="brak\npodglądu")
                    return
                try:
                    img = Image.open(io.BytesIO(raw))
                    img.thumbnail(_THUMB_SIZE, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    thumb_refs.append(photo)
                    label.configure(image=photo, text="")
                except OSError:
                    label.configure(image="", text="błąd\npodglądu")

            host.after(0, done)

        label.configure(image="", text="ładowanie…")
        threading.Thread(target=worker, daemon=True).start()

    def _build_media_row(parent: ttk.Frame, *, slot: str, is_video: bool, initial: str) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x")
        thumb = tk.Label(row, width=18, height=6, relief="groove", bg="#eee", anchor="center")
        thumb.pack(side="left", padx=(0, 10))
        meta = ttk.Frame(row)
        meta.pack(side="left", fill="x", expand=True)
        name_var = tk.StringVar(value=shopify_ref_label(initial) if initial else "(brak)")
        set_widget(slot, name_var)
        set_widget(f"{slot}__full", initial)
        set_widget(f"{slot}__thumb", thumb)
        ttk.Label(meta, textvariable=name_var, foreground="#333").pack(anchor="w")
        allowed = _VIDEO_SUFFIXES if is_video else _IMAGE_SUFFIXES
        upload_label = "Wgraj film…" if is_video else "Wgraj grafikę…"

        def _apply_ref(full: str) -> None:
            name_var.set(shopify_ref_label(full) if full else "(brak)")
            set_widget(f"{slot}__full", full)
            _set_thumb(thumb, full)
            if full and not overlay_off_var.get():
                overlay_pct_var.set(
                    normalize_overlay_pct(
                        get_widget(f"{bg_field_id}__overlay_stash") or DEFAULT_SECTION_OVERLAY_PCT
                    )
                )
            _set_overlay_controls_enabled(bool(full))
            _update_overlay_label()
            _persist_bg_from_widgets()
            mark_dirty()

        def _upload_path(path: Path) -> None:
            if path.suffix.lower() not in allowed:
                kinds = "MP4, WebM, MOV" if is_video else "JPG, PNG, WebP"
                messagebox.showerror(app_title, f"Dozwolone: {kinds}.", parent=dlg)
                return
            try:
                full = upload_shopify_video(path) if is_video else upload_shopify_image(path)
                _apply_ref(full)
                show_toast(host, f"Wgrano {shopify_ref_label(full)}", duration_ms=1400)
            except Exception as exc:
                messagebox.showerror(app_title, str(exc), parent=dlg)

        def _pick() -> None:
            if is_video:
                filetypes = [("Filmy", "*.mp4 *.webm *.mov"), ("Wszystkie", "*.*")]
            else:
                filetypes = [("Obrazy", "*.jpg *.jpeg *.png *.webp"), ("Wszystkie", "*.*")]
            path = filedialog.askopenfilename(parent=dlg, filetypes=filetypes)
            if path:
                _upload_path(Path(path))

        def _clear() -> None:
            _apply_ref("")
            if status_var is not None:
                status_var.set(f"Usunięto {'film' if is_video else 'grafikę'} tła.")
            show_toast(host, f"Usunięto {'film' if is_video else 'grafikę'}", duration_ms=1200)

        def _on_drop(event: Any) -> None:
            paths = parse_dnd_files(getattr(event, "data", "") or "")
            matched = [p for p in paths if p.suffix.lower() in allowed]
            if matched:
                _upload_path(matched[0])

        btn_row = ttk.Frame(meta)
        btn_row.pack(anchor="w", pady=(4, 0))
        ttk.Button(btn_row, text=upload_label, command=_pick).pack(side="left")
        ttk.Button(
            btn_row,
            text="Usuń film" if is_video else "Usuń grafikę",
            command=_clear,
        ).pack(side="left", padx=(8, 0))
        register_drop_target(thumb, on_drop=_on_drop)
        ttk.Label(meta, text="lub przeciągnij plik na miniaturę", foreground="#888").pack(anchor="w", pady=(2, 0))
        _set_thumb(thumb, initial)

    image_initial = bg.get("ref", "") if bg.get("media") == "image" else ""
    video_initial = bg.get("ref", "") if bg.get("media") == "video" else ""
    _build_media_row(image_frame, slot=f"{bg_field_id}__image", is_video=False, initial=str(image_initial))
    _build_media_row(video_frame, slot=f"{bg_field_id}__video", is_video=True, initial=str(video_initial))

    crop_host = ttk.Frame(image_frame)
    crop_host.pack(fill="x", pady=(8, 0))
    oy_var = build_object_y_controls(
        crop_host,
        initial=bg.get("object_y"),
        on_change=lambda _value: (_persist_bg_from_widgets(), mark_dirty()),
    )
    set_widget(f"{bg_field_id}__object_y", oy_var)

    def _sync_bg_media(*_args: object) -> None:
        image_frame.pack_forget()
        video_frame.pack_forget()
        if media_var.get() == "video":
            video_frame.pack(fill="x")
        else:
            image_frame.pack(fill="x")
        _set_overlay_controls_enabled(_bg_has_media())
        _update_overlay_label()
        _persist_bg_from_widgets()
        mark_dirty()

    media_var.trace_add("write", _sync_bg_media)
    _sync_bg_media()
    _update_overlay_label()

    def _clear_background() -> None:
        for slot in (f"{bg_field_id}__image", f"{bg_field_id}__video"):
            set_widget(f"{slot}__full", "")
            var = get_widget(slot)
            if var is not None and hasattr(var, "set"):
                var.set("(brak)")
            thumb = get_widget(f"{slot}__thumb")
            if thumb is not None:
                _set_thumb(thumb, "")
        overlay_off_var.set(True)
        overlay_pct_var.set(overlay_stash)
        set_zone_bg(
            {"media": "none", "ref": "", "overlay_pct": 0, "object_y": normalize_object_y(None)}
        )
        _set_overlay_controls_enabled(False)
        _update_overlay_label()
        mark_dirty()
        if status_var is not None:
            status_var.set("Usunięto tło sekcji.")
        show_toast(host, "Tło usunięte", duration_ms=1400)

    def _close() -> None:
        _persist_bg_from_widgets()
        dlg.destroy()

    btn_row = ttk.Frame(pad)
    btn_row.pack(fill="x", pady=(12, 0))
    ttk.Button(btn_row, text="Usuń tło", command=_clear_background).pack(side="left")
    ttk.Button(btn_row, text="Zamknij", command=_close).pack(side="right")
    dlg.protocol("WM_DELETE_WINDOW", _close)
