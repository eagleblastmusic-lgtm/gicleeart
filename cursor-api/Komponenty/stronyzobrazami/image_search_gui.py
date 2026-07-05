"""Zakladka wyszukiwania po obrazie (reverse image + podobienstwo graficzne)."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES  # type: ignore

    _HAS_DND = True
except ImportError:
    _HAS_DND = False

from Komponenty._shared.tkdnd_safe import register_drop_target
from Komponenty._shared.toast import show_toast
from PIL import Image, ImageTk

from .search.image_search import search_by_image
from .search.preview_urls import artwork_preview_url
from .search.registry import sources_for_sites
from .search.reverse_urls import serpapi_key
from .search.thumbnails import bytes_to_photo, fetch_thumbnail_bytes, get_cached_bytes
from .search.types import ArtworkHit
from .settings import load_settings, save_settings
from .source_checkboxes import mount_scrollable_source_list, refresh_source_list_scroll
from .storage import SiteStore

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def _parse_dnd_files(data: str) -> list[Path]:
    out: list[Path] = []
    buf = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            buf = ""
        elif ch == "}":
            in_brace = False
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        elif ch == " " and not in_brace:
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(Path(buf.strip()))
    return out


def _is_image_path(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _IMAGE_EXTS


def build_image_search_tab(parent: tk.Misc, root: tk.Misc, *, get_store: Callable[[], SiteStore]) -> None:
    state: dict[str, object] = {"running": False, "hits": [], "image_path": ""}
    app_settings = load_settings()

    top = ttk.Frame(parent, padding=(12, 10, 12, 6))
    top.pack(fill="x")
    ttk.Label(top, text="Szukaj po obrazie", font=("Segoe UI", 13, "bold")).pack(side="left")

    key_row = ttk.Frame(parent, padding=(12, 0, 12, 4))
    key_row.pack(fill="x")
    key_label = ttk.Label(key_row, text="SERPAPI_KEY: …")
    key_label.pack(side="left")

    def _update_key_label() -> None:
        key = serpapi_key()
        if key:
            hint = "..." + key[-6:] if len(key) > 6 else key
            key_label.configure(
                text=f"SERPAPI_KEY: OK ({hint}, cursor-api/.env)",
                foreground="#0a6",
            )
        else:
            key_label.configure(
                text="SERPAPI_KEY: BRAK — reverse image wymaga klucza SerpAPI",
                foreground="#a60",
            )

    _update_key_label()

    hint = ttk.Label(
        parent,
        text=(
            "Przeciagnij obraz (lub kliknij pole) i szukaj w muzeach z Twoich zakladek. "
            "Silnik: reverse image (Google Lens / Yandex / Bing przez SerpAPI), "
            "potem porownanie graficzne miniatur (dHash)."
        ),
        wraplength=920,
        foreground="#555",
        padding=(12, 0, 12, 8),
    )
    hint.pack(fill="x")

    drop_note = "" if _HAS_DND else " (brak DnD: pip install tkinterdnd2)"
    drop_frame = ttk.LabelFrame(parent, text=f"Obraz zrodlowy{drop_note}", padding=(8, 6))
    drop_frame.pack(fill="x", padx=12, pady=(0, 8))

    drop_inner = ttk.Frame(drop_frame)
    drop_inner.pack(fill="x")

    drop_label = tk.Label(
        drop_inner,
        text="Przeciagnij obraz tutaj\nlub kliknij, aby wybrac plik",
        bg="#f4f4f4",
        fg="#666",
        width=48,
        height=8,
        cursor="hand2",
        justify="center",
    )
    drop_label.pack(side="left", fill="both", expand=True, padx=(0, 8))

    meta_var = tk.StringVar(value="Brak obrazu.")
    ttk.Label(drop_inner, textvariable=meta_var, wraplength=320, foreground="#444").pack(
        side="left",
        fill="y",
        anchor="n",
    )

    drop_photo: dict[str, object] = {"img": None}

    def _show_preview_image(path: Path) -> None:
        try:
            img = Image.open(path)
            img.thumbnail((220, 160), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
        except (OSError, ValueError) as exc:
            drop_label.configure(
                image="",
                text=f"Nie udalo sie wczytac:\n{exc}",
                bg="#fff3e0",
                fg="#a60",
            )
            drop_photo["img"] = None
            return
        drop_label.configure(image=photo, text="", bg="#ffffff")
        drop_photo["img"] = photo
        w, h = Image.open(path).size
        meta_var.set(f"{path.name}\n{w}×{h} px\n{path.parent}")

    def _set_image(path: Path) -> None:
        if not _is_image_path(path):
            messagebox.showwarning("Szukaj po obrazie", "Wybierz plik obrazu (JPG, PNG, WebP…).", parent=root)
            return
        state["image_path"] = str(path)
        _show_preview_image(path)

    def _browse() -> None:
        path = filedialog.askopenfilename(
            parent=root,
            title="Wybierz obraz",
            filetypes=[
                ("Obrazy", "*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tif *.tiff"),
                ("Wszystkie", "*.*"),
            ],
        )
        if path:
            _set_image(Path(path))

    drop_label.bind("<Button-1>", lambda _e: _browse())

    def _on_drop(event: tk.Event) -> None:  # type: ignore[type-arg]
        paths = _parse_dnd_files(event.data)
        if paths:
            _set_image(paths[0])

    register_drop_target(drop_label, on_drop=_on_drop)

    src_frame = ttk.LabelFrame(parent, text="Zrodla (z zakladek)", padding=(8, 6))
    src_frame.pack(fill="x", padx=12, pady=(0, 8))
    src_vars: dict[str, tk.BooleanVar] = {}
    src_inner = mount_scrollable_source_list(src_frame, height=120)

    def _persist_settings() -> None:
        app_settings.source_checked = {sid: var.get() for sid, var in src_vars.items()}
        save_settings(app_settings)

    def _refresh_sources() -> None:
        prev = {sid: var.get() for sid, var in src_vars.items()}
        saved = app_settings.source_checked
        for child in src_inner.winfo_children():
            child.destroy()
        src_vars.clear()
        detected = sources_for_sites(get_store().sorted())
        if not detected:
            ttk.Label(
                src_inner,
                text="Dodaj linki muzeow w zakladce «Zakladki».",
                foreground="#a60",
            ).pack(anchor="w")
            return
        for idx, src in enumerate(detected):
            default = prev.get(src.source_id, saved.get(src.source_id, True))
            var = tk.BooleanVar(value=default)
            var.trace_add("write", lambda *_a: _persist_settings())
            src_vars[src.source_id] = var
            ttk.Checkbutton(src_inner, text=src.name, variable=var).grid(
                row=idx // 2,
                column=idx % 2,
                sticky="w",
                padx=(0, 16),
                pady=2,
            )
        refresh_source_list_scroll(src_inner)

    btn_row = ttk.Frame(parent, padding=(12, 0, 12, 6))
    btn_row.pack(fill="x")
    search_btn = ttk.Button(btn_row, text="Szukaj po grafice")
    search_btn.pack(side="left")
    stop_btn = ttk.Button(btn_row, text="Stop", state="disabled")
    stop_btn.pack(side="left", padx=(8, 0))
    download_btn = ttk.Button(btn_row, text="Pobierz obraz (HD)")
    download_btn.pack(side="left", padx=(8, 0))
    open_link_btn = ttk.Button(btn_row, text="Otworz link")
    open_link_btn.pack(side="left", padx=(8, 0))
    status_var = tk.StringVar(value="Gotowy.")
    ttk.Label(btn_row, textvariable=status_var, foreground="#444").pack(side="right")

    outer = ttk.Frame(parent, padding=(12, 0, 12, 8))
    outer.pack(fill="both", expand=True)
    paned = ttk.Panedwindow(outer, orient="horizontal")
    paned.pack(fill="both", expand=True)

    left_col = ttk.Frame(paned)
    paned.add(left_col, weight=3)
    results_frame = ttk.LabelFrame(left_col, text="Wyniki", padding=(8, 6))
    results_frame.pack(fill="both", expand=True)

    notes_frame = ttk.LabelFrame(left_col, text="Informacje", padding=(8, 4))
    notes_frame.pack(fill="x", pady=(8, 0))
    notes_list = tk.Listbox(notes_frame, height=3, font=("Segoe UI", 9), fg="#666")
    notes_list.pack(fill="x")

    preview_frame = ttk.LabelFrame(paned, text="Podglad wyniku", padding=(8, 6))
    paned.add(preview_frame, weight=1)
    preview_label = tk.Label(
        preview_frame,
        text="Zaznacz wiersz,\naby zobaczyc miniaturke.",
        bg="#f4f4f4",
        fg="#666",
        width=28,
        height=12,
        justify="center",
    )
    preview_label.pack(fill="both", expand=True)
    preview_label._thumb_photo = None  # type: ignore[attr-defined]

    cols = ("score", "source", "artist", "title", "url")
    tree = ttk.Treeview(results_frame, columns=cols, show="headings", selectmode="browse")
    tree.heading("score", text="Podob.")
    tree.heading("source", text="Zrodlo")
    tree.heading("artist", text="Artysta")
    tree.heading("title", text="Tytul")
    tree.heading("url", text="URL")
    tree.column("score", width=56, stretch=False)
    tree.column("source", width=140, stretch=False)
    tree.column("artist", width=140, stretch=True)
    tree.column("title", width=200, stretch=True)
    tree.column("url", width=260, stretch=True)
    scroll = ttk.Scrollbar(results_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    cancel_event = threading.Event()
    preview_token = {"n": 0}
    download_state = {"running": False}

    def _selected_source_ids() -> list[str]:
        return [sid for sid, var in src_vars.items() if var.get()]

    def _fill_notes(lines: list[str]) -> None:
        notes_list.delete(0, "end")
        for line in lines:
            notes_list.insert("end", line)

    def _fill_results(hits: list[ArtworkHit]) -> None:
        tree.delete(*tree.get_children())
        state["hits"] = hits
        for idx, hit in enumerate(hits):
            tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    f"{hit.score:.0f}%",
                    hit.source_name,
                    hit.artist,
                    hit.title,
                    hit.object_url,
                ),
            )
        if hits:
            tree.selection_set("0")
            tree.focus("0")
            _show_preview_for_index(0)

    def _clear_preview() -> None:
        preview_label.configure(
            image="",
            text="Zaznacz wiersz,\naby zobaczyc miniaturke.",
            bg="#f4f4f4",
            fg="#666",
        )
        preview_label._thumb_photo = None  # type: ignore[attr-defined]

    def _show_preview_for_index(idx: int) -> None:
        hits: list[ArtworkHit] = state.get("hits") or []
        if idx < 0 or idx >= len(hits):
            _clear_preview()
            return
        hit = hits[idx]
        preview_token["n"] += 1
        token = preview_token["n"]
        preview_label.configure(image="", text="Laduje…", bg="#f4f4f4", fg="#666")

        def work() -> None:
            preview_url = artwork_preview_url(hit)
            if not preview_url:

                def no_image() -> None:
                    if preview_token["n"] != token:
                        return
                    preview_label.configure(image="", text="Brak miniatury", bg="#f4f4f4", fg="#888")
                    preview_label._thumb_photo = None  # type: ignore[attr-defined]

                root.after(0, no_image)
                return

            cached = get_cached_bytes(preview_url)
            if cached:

                def show_cached() -> None:
                    if preview_token["n"] != token:
                        return
                    try:
                        photo = bytes_to_photo(cached)
                        preview_label.configure(image=photo, text="", bg="#ffffff")
                        preview_label._thumb_photo = photo  # type: ignore[attr-defined]
                    except (ImportError, OSError, ValueError):
                        _clear_preview()

                root.after(0, show_cached)
                return

            raw = fetch_thumbnail_bytes(preview_url)
            if raw is None or preview_token["n"] != token:
                return

            def ok() -> None:
                if preview_token["n"] != token:
                    return
                try:
                    photo = bytes_to_photo(raw)
                    preview_label.configure(image=photo, text="", bg="#ffffff")
                    preview_label._thumb_photo = photo  # type: ignore[attr-defined]
                except (ImportError, OSError, ValueError):
                    _clear_preview()

            root.after(0, ok)

        threading.Thread(target=work, daemon=True, name="stronyzobrazami-img-prev").start()

    tree.bind("<<TreeviewSelect>>", lambda _e: _show_preview_for_index(int(tree.selection()[0])) if tree.selection() else None)

    def _open_hit(_event: tk.Event | None = None) -> None:
        sel = tree.selection()
        if not sel:
            return
        hits: list[ArtworkHit] = state.get("hits") or []
        try:
            hit = hits[int(sel[0])]
        except (IndexError, ValueError):
            return
        if hit.object_url:
            webbrowser.open(hit.object_url)

    tree.bind("<Double-1>", _open_hit)
    tree.bind("<Return>", _open_hit)
    open_link_btn.configure(command=lambda: _open_hit())

    def _download_selected() -> None:
        if download_state["running"]:
            return
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Pobierz obraz", "Zaznacz wiersz z wynikiem.", parent=root)
            return
        hits: list[ArtworkHit] = state.get("hits") or []
        try:
            hit = hits[int(sel[0])]
        except (IndexError, ValueError):
            return
        from .download_gui import run_download_for_hit

        download_state["running"] = True
        download_btn.configure(state="disabled")
        status_var.set("Pobieranie obrazu…")

        def _done() -> None:
            download_state["running"] = False
            download_btn.configure(state="normal")

        run_download_for_hit(
            root,
            hit,
            log=lambda msg: root.after(0, lambda m=msg: status_var.set(m)),
            on_done=_done,
        )

    download_btn.configure(command=_download_selected)

    def _run_search() -> None:
        if state["running"]:
            return
        img_path = str(state.get("image_path") or "")
        if not img_path:
            messagebox.showinfo("Szukaj po obrazie", "Najpierw wybierz lub przeciagnij obraz.", parent=root)
            return
        selected = _selected_source_ids()
        if not selected:
            messagebox.showinfo("Szukaj po obrazie", "Zaznacz co najmniej jedno zrodlo.", parent=root)
            return

        cancel_event.clear()
        state["running"] = True
        search_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        status_var.set("Szukam…")
        _update_key_label()

        def work() -> None:
            result = search_by_image(
                img_path,
                sites=get_store().sorted(),
                source_ids=selected,
                limit_per_source=app_settings.search_limit,
                on_status=lambda msg: root.after(0, lambda m=msg: status_var.set(m)),
                cancel_event=cancel_event,
            )
            hits = result.sorted_hits()

            def _ui() -> None:
                _fill_results(hits)
                _fill_notes(result.notes)
                if result.cancelled:
                    msg = f"Anulowano — {len(hits)} wynik(ow)."
                elif hits:
                    msg = f"Znaleziono {len(hits)} dopasowan graficznych."
                else:
                    msg = "Brak dopasowan — sprobuj innego zdjecia lub zrodla."
                status_var.set(msg)
                show_toast(root, msg, duration_ms=2200)

            root.after(0, _ui)
            root.after(0, _done)

        def _done() -> None:
            state["running"] = False
            search_btn.configure(state="normal")
            stop_btn.configure(state="disabled")

        threading.Thread(target=work, daemon=True, name="stronyzobrazami-img-search").start()

    def _stop() -> None:
        cancel_event.set()
        status_var.set("Anulowanie…")

    search_btn.configure(command=_run_search)
    stop_btn.configure(command=_stop)

    _refresh_sources()
    parent.bind("<Visibility>", lambda _e: _refresh_sources(), add="+")
    parent._refresh_image_search_sources = _refresh_sources  # type: ignore[attr-defined]
