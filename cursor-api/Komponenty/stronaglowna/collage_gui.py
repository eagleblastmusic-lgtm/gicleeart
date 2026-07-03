"""Edytor kolażu wideo w GUI Strona główna."""

from __future__ import annotations

import copy
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.window_geometry import position_toplevel_screen_center
from PIL import Image, ImageTk

from .video_picker import pick_shopify_video
from .video_preview import preview_shopify_video
from .service import VIDEO_SUFFIXES, fetch_thumbnail_bytes, shopify_ref_label, upload_shopify_video
from .video_collage import (
    DEFAULT_TRANSITION_IN,
    DEFAULT_TRANSITION_IN_MS,
    DEFAULT_TRANSITION_OUT,
    DEFAULT_TRANSITION_OUT_MS,
    ENTRY_TRANSITIONS,
    EXIT_TRANSITIONS,
    apply_cross_preset,
    parse_collage,
)

_ENTRY_LABELS = {k: v for k, v in ENTRY_TRANSITIONS}
_ENTRY_IDS = {v: k for k, v in ENTRY_TRANSITIONS}
_EXIT_LABELS = {k: v for k, v in EXIT_TRANSITIONS}
_EXIT_IDS = {v: k for k, v in EXIT_TRANSITIONS}

APP_TITLE = "Strona główna — landing page"
_COLLAGE_WIN_TITLE = "Kolaż wideo — hero"
_THUMB = (96, 72)


def collage_summary_text(model: dict[str, Any] | None) -> str:
    data = parse_collage(model or {})
    clips = data.get("clips") or []
    if not clips:
        return "Brak klipów — otwórz edytor i dodaj filmy."
    loop = "zapętlanie wł." if data.get("loop", True) else "bez zapętlania"
    names: list[str] = []
    for clip in clips[:4]:
        ref = str(clip.get("video") or "")
        names.append(str(clip.get("label") or shopify_ref_label(ref)))
    tail = f" … +{len(clips) - 4}" if len(clips) > 4 else ""
    return f"{len(clips)} klip(ów), {loop}: " + ", ".join(names) + tail


def _clip_defaults(*, is_first: bool) -> dict[str, Any]:
    return {
        "transition_in": DEFAULT_TRANSITION_IN,
        "transition_out": DEFAULT_TRANSITION_OUT,
        "transition_in_ms": DEFAULT_TRANSITION_IN_MS,
        "transition_out_ms": DEFAULT_TRANSITION_OUT_MS,
        "cross_effect": not is_first,
    }


def _collage_model(state: dict[str, Any]) -> dict[str, Any]:
    model = state["widgets"].get("hero_video_collage")
    if not isinstance(model, dict):
        model = parse_collage(model)
        state["widgets"]["hero_video_collage"] = model
    return model


def build_collage_editor(
    parent: ttk.Frame,
    *,
    host: tk.Misc,
    state: dict[str, Any],
    mark_dirty: Callable[[], None],
    status_var: tk.StringVar,
    show_toast: Callable[..., None],
    on_change: Callable[[], None] | None = None,
) -> None:
    model = _collage_model(state)

    def _changed() -> None:
        mark_dirty()
        if on_change:
            on_change()

    header = ttk.Frame(parent)
    header.pack(fill="x", pady=(0, 8))
    loop_var = tk.BooleanVar(value=bool(model.get("loop", True)))
    state["widgets"]["hero_collage_loop"] = loop_var
    ttk.Checkbutton(
        header,
        text="Zapętlaj kolaż po ostatnim klipie",
        variable=loop_var,
        command=lambda: (_sync_loop(), _changed()),
    ).pack(anchor="w")

    list_host = ttk.Frame(parent)
    list_host.pack(fill="both", expand=True)

    canvas = tk.Canvas(list_host, highlightthickness=0, height=420)
    scroll = ttk.Scrollbar(list_host, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    row_refs: list[dict[str, Any]] = []

    def _sync_loop() -> None:
        model["loop"] = bool(loop_var.get())

    def _rebuild() -> None:
        for child in inner.winfo_children():
            child.destroy()
        row_refs.clear()
        clips = model.get("clips") or []
        if not clips:
            ttk.Label(
                inner,
                text="Brak klipów. Kliknij «Dodaj wideo…».",
                foreground="#777",
            ).pack(anchor="w", pady=8, padx=4)
            return

        for idx, clip in enumerate(clips):
            _build_row(idx, clip)

    def _move(idx: int, delta: int) -> None:
        clips = model.setdefault("clips", [])
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(clips):
            return
        clips[idx], clips[new_idx] = clips[new_idx], clips[idx]
        if new_idx == 0:
            clips[0]["cross_effect"] = False
        _changed()
        _rebuild()

    def _remove(idx: int) -> None:
        clips = model.get("clips") or []
        if idx < 0 or idx >= len(clips):
            return
        if not messagebox.askyesno(APP_TITLE, "Usunąć ten klip z kolażu?", parent=host):
            return
        clips.pop(idx)
        if clips:
            clips[0]["cross_effect"] = False
        _changed()
        _rebuild()

    def _set_field(idx: int, key: str, value: Any) -> None:
        clips = model.get("clips") or []
        if 0 <= idx < len(clips):
            clips[idx][key] = value
            _changed()

    def _set_in_ms(idx: int, value: str) -> None:
        clips = model.get("clips") or []
        if 0 <= idx < len(clips):
            try:
                clips[idx]["transition_in_ms"] = max(150, min(4000, int(value)))
            except ValueError:
                clips[idx]["transition_in_ms"] = DEFAULT_TRANSITION_IN_MS
            _changed()

    def _set_out_ms(idx: int, value: str) -> None:
        clips = model.get("clips") or []
        if 0 <= idx < len(clips):
            try:
                clips[idx]["transition_out_ms"] = max(150, min(4000, int(value)))
            except ValueError:
                clips[idx]["transition_out_ms"] = DEFAULT_TRANSITION_OUT_MS
            _changed()

    def _apply_cross(idx: int) -> None:
        clips = model.get("clips") or []
        apply_cross_preset(clips, idx)
        _changed()
        _rebuild()
        show_toast(host, "Cross: fade out poprzedniego + fade in tego klipu", duration_ms=1600)

    def _toggle_cross(idx: int, enabled: bool) -> None:
        clips = model.get("clips") or []
        _set_field(idx, "cross_effect", enabled)
        if enabled:
            apply_cross_preset(clips, idx)
            _changed()
            _rebuild()

    def _build_row(idx: int, clip: dict[str, Any]) -> None:
        row = ttk.LabelFrame(inner, text=f"Klip {idx + 1}", padding=8)
        row.pack(fill="x", pady=(0, 8), padx=2)

        top = ttk.Frame(row)
        top.pack(fill="x")

        thumb = ttk.Label(top, text="…", width=14, anchor="center")
        thumb.pack(side="left", padx=(0, 8))

        meta = ttk.Frame(top)
        meta.pack(side="left", fill="x", expand=True)

        ref = str(clip.get("video") or "")
        label = str(clip.get("label") or shopify_ref_label(ref))
        name_lbl = ttk.Label(meta, text=label, font=("", 9, "bold"))
        name_lbl.pack(anchor="w")
        ref_lbl = ttk.Label(meta, text=ref or "(brak)", foreground="#666", wraplength=520)
        ref_lbl.pack(anchor="w")

        def _preview_clip(_evt: object = None) -> None:
            if ref:
                preview_shopify_video(host, ref, title=f"Podgląd — {label}")

        for w in (thumb, name_lbl, ref_lbl):
            w.bind("<Double-1>", _preview_clip)
            w.configure(cursor="hand2")

        fx = ttk.Frame(meta)
        fx.pack(anchor="w", fill="x", pady=(6, 0))

        in_row = ttk.Frame(fx)
        in_row.pack(anchor="w", fill="x")
        ttk.Label(in_row, text="Wejście:", width=12).pack(side="left")
        in_var = tk.StringVar(
            value=_ENTRY_LABELS.get(str(clip.get("transition_in") or DEFAULT_TRANSITION_IN), DEFAULT_TRANSITION_IN)
        )
        ttk.Combobox(
            in_row,
            textvariable=in_var,
            values=[t[1] for t in ENTRY_TRANSITIONS],
            width=22,
            state="readonly",
        ).pack(side="left", padx=(4, 0))
        ttk.Label(in_row, text="ms:", foreground="#666").pack(side="left", padx=(8, 2))
        in_ms_var = tk.StringVar(value=str(clip.get("transition_in_ms") or DEFAULT_TRANSITION_IN_MS))
        ttk.Spinbox(in_row, from_=150, to=4000, increment=50, textvariable=in_ms_var, width=6).pack(side="left")
        if idx == 0:
            ttk.Label(in_row, text="(start kolażu)", foreground="#777").pack(side="left", padx=(6, 0))

        out_row = ttk.Frame(fx)
        out_row.pack(anchor="w", fill="x", pady=(4, 0))
        ttk.Label(out_row, text="Wyjście:", width=12).pack(side="left")
        out_var = tk.StringVar(
            value=_EXIT_LABELS.get(str(clip.get("transition_out") or DEFAULT_TRANSITION_OUT), DEFAULT_TRANSITION_OUT)
        )
        ttk.Combobox(
            out_row,
            textvariable=out_var,
            values=[t[1] for t in EXIT_TRANSITIONS],
            width=22,
            state="readonly",
        ).pack(side="left", padx=(4, 0))
        ttk.Label(out_row, text="ms:", foreground="#666").pack(side="left", padx=(8, 2))
        out_ms_var = tk.StringVar(value=str(clip.get("transition_out_ms") or DEFAULT_TRANSITION_OUT_MS))
        ttk.Spinbox(out_row, from_=150, to=4000, increment=50, textvariable=out_ms_var, width=6).pack(side="left")
        ttk.Label(out_row, text="(start przed końcem klipu)", foreground="#777").pack(side="left", padx=(6, 0))

        cross_row = ttk.Frame(fx)
        cross_row.pack(anchor="w", pady=(6, 0))
        cross_var = tk.BooleanVar(value=bool(clip.get("cross_effect")))
        if idx == 0:
            ttk.Label(cross_row, text="Cross effect: tylko od klipu 2", foreground="#777").pack(side="left")
        else:
            ttk.Checkbutton(
                cross_row,
                text="Cross effect (równoczesne wyjście + wejście)",
                variable=cross_var,
                command=lambda i=idx, v=cross_var: _toggle_cross(i, v.get()),
            ).pack(side="left")
            ttk.Button(
                cross_row,
                text="Cross: fade out → fade in",
                command=lambda i=idx: _apply_cross(i),
            ).pack(side="left", padx=(8, 0))

        in_var.trace_add(
            "write",
            lambda *_a, i=idx, v=in_var: (
                _set_field(i, "transition_in", _ENTRY_IDS.get(v.get(), DEFAULT_TRANSITION_IN)),
                _set_field(i, "cross_effect", False) if i > 0 else None,
            ),
        )
        out_var.trace_add(
            "write",
            lambda *_a, i=idx, v=out_var: (
                _set_field(i, "transition_out", _EXIT_IDS.get(v.get(), DEFAULT_TRANSITION_OUT)),
            ),
        )
        in_ms_var.trace_add("write", lambda *_a, i=idx, v=in_ms_var: _set_in_ms(i, v.get()))
        out_ms_var.trace_add("write", lambda *_a, i=idx, v=out_ms_var: _set_out_ms(i, v.get()))

        btns = ttk.Frame(row)
        btns.pack(anchor="e", pady=(6, 0))
        if idx > 0:
            ttk.Button(btns, text="↑", width=3, command=lambda i=idx: _move(i, -1)).pack(side="left")
        if idx < len(model.get("clips") or []) - 1:
            ttk.Button(btns, text="↓", width=3, command=lambda i=idx: _move(i, 1)).pack(side="left", padx=(4, 0))
        ttk.Button(btns, text="Usuń", command=lambda i=idx: _remove(i)).pack(side="left", padx=(8, 0))

        def _load_thumb() -> None:
            raw = fetch_thumbnail_bytes(shopify_ref=ref)

            def done() -> None:
                if raw is None:
                    thumb.configure(text="wideo", image="")
                    return
                try:
                    img = Image.open(__import__("io").BytesIO(raw))
                    img.thumbnail(_THUMB, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    thumb.configure(image=photo, text="")
                    thumb.image = photo
                except Exception:
                    thumb.configure(text="wideo", image="")

            host.after(0, done)

        if ref:
            threading.Thread(target=_load_thumb, daemon=True).start()

        row_refs.append({"clip": clip, "in_var": in_var, "out_var": out_var, "in_ms_var": in_ms_var, "out_ms_var": out_ms_var})

    def _append_clip(ref: str, label: str) -> None:
        clips = model.setdefault("clips", [])
        defaults = _clip_defaults(is_first=(len(clips) == 0))
        clips.append({"video": ref, "label": label, **defaults})

    def _add_videos(paths: list[Path]) -> None:
        for p in paths:
            if p.suffix.lower() not in VIDEO_SUFFIXES:
                messagebox.showerror(
                    APP_TITLE,
                    f"Pominięto {p.name} — dozwolone: MP4, WebM, MOV.",
                    parent=host,
                )
                continue
            status_var.set(f"Wgrywam: {p.name}…")

            def worker(path: Path = p) -> None:
                try:
                    ref = upload_shopify_video(path)

                    def done() -> None:
                        _append_clip(ref, path.stem)
                        _changed()
                        _rebuild()
                        status_var.set(f"Dodano klip: {path.name}")
                        show_toast(host, f"Dodano {path.name}")

                    host.after(0, done)
                except Exception as exc:
                    host.after(
                        0,
                        lambda e=str(exc): messagebox.showerror(APP_TITLE, e, parent=host),
                    )

            threading.Thread(target=worker, daemon=True).start()

    def _add_from_library() -> None:
        ref = pick_shopify_video(host, title="Dodaj klip z listy filmów")
        if not ref:
            return
        _append_clip(ref, shopify_ref_label(ref))
        _changed()
        _rebuild()
        status_var.set(f"Dodano klip: {shopify_ref_label(ref)}")
        show_toast(host, f"Dodano {shopify_ref_label(ref)}")

    def _pick_videos() -> None:
        paths = filedialog.askopenfilenames(
            parent=host,
            title="Dodaj klipy wideo do kolażu",
            filetypes=[("Filmy", "*.mp4 *.webm *.mov"), ("Wszystkie", "*.*")],
        )
        if not paths:
            return
        _add_videos([Path(p) for p in paths])

    toolbar = ttk.Frame(parent)
    toolbar.pack(fill="x", pady=(8, 0))
    ttk.Button(toolbar, text="Dodaj wideo…", command=_pick_videos).pack(side="left")
    ttk.Button(toolbar, text="Z listy…", command=_add_from_library).pack(side="left", padx=(8, 0))
    ttk.Label(
        parent,
        text=(
            "Wejście = efekt + czas (ms) przy starcie klipu. Wyjście = efekt + czas (ms) przed następnym klipsem "
            "(przejście startuje tyle ms przed końcem). Cross effect = oba naraz. "
            "Dwuklik na miniaturę / nazwę klipu = podgląd filmu."
        ),
        foreground="#777",
        wraplength=720,
    ).pack(anchor="w", pady=(8, 0))

    _rebuild()


def open_collage_editor_window(
    parent: tk.Misc,
    *,
    state: dict[str, Any],
    mark_dirty: Callable[[], None],
    status_var: tk.StringVar,
    show_toast: Callable[..., None],
    on_close: Callable[[], None] | None = None,
) -> None:
    existing = state["widgets"].get("hero_collage_editor_win")
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                existing.focus_force()
                return
        except tk.TclError:
            pass

    win = tk.Toplevel(parent)
    win.title(_COLLAGE_WIN_TITLE)
    position_toplevel_screen_center(win, 900, 720)
    win.transient(parent.winfo_toplevel())
    state["widgets"]["hero_collage_editor_win"] = win

    body = ttk.Frame(win, padding=(12, 10))
    body.pack(fill="both", expand=True)

    def _refresh_summary() -> None:
        summary = state["widgets"].get("hero_collage_summary")
        if isinstance(summary, tk.StringVar):
            summary.set(collage_summary_text(_collage_model(state)))

    build_collage_editor(
        body,
        host=win,
        state=state,
        mark_dirty=mark_dirty,
        status_var=status_var,
        show_toast=show_toast,
        on_change=_refresh_summary,
    )

    footer = ttk.Frame(win, padding=(12, 10))
    footer.pack(fill="x")

    def _close() -> None:
        state["widgets"].pop("hero_collage_editor_win", None)
        _refresh_summary()
        if on_close:
            on_close()
        win.destroy()

    ttk.Button(footer, text="Zamknij", command=_close).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", _close)


def add_collage_launcher(
    parent: ttk.Frame,
    *,
    host: tk.Misc,
    initial: Any,
    state: dict[str, Any],
    mark_dirty: Callable[[], None],
    status_var: tk.StringVar,
    show_toast: Callable[..., None],
) -> None:
    """Kompaktowy panel w hero: podsumowanie + przycisk otwierający pełny edytor."""
    state["widgets"]["hero_video_collage"] = copy.deepcopy(parse_collage(initial))

    summary_var = tk.StringVar(value=collage_summary_text(state["widgets"]["hero_video_collage"]))
    state["widgets"]["hero_collage_summary"] = summary_var

    ttk.Label(
        parent,
        text="Kolaż składa się z wielu klipów wideo z własnymi przejściami.",
        foreground="#777",
        wraplength=520,
    ).pack(anchor="w")

    summary_lbl = ttk.Label(parent, textvariable=summary_var, wraplength=520)
    summary_lbl.pack(anchor="w", pady=(6, 0))

    def _open() -> None:
        open_collage_editor_window(
            host,
            state=state,
            mark_dirty=mark_dirty,
            status_var=status_var,
            show_toast=show_toast,
            on_close=lambda: summary_var.set(collage_summary_text(_collage_model(state))),
        )

    ttk.Button(parent, text="Edytuj kolaż wideo…", command=_open).pack(anchor="w", pady=(10, 0))


# Zachowanie wsteczne (testy / importy)
add_collage_editor = build_collage_editor
