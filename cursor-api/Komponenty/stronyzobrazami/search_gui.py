"""Zakladka wyszukiwania w kolekcjach muzealnych."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .search import search_collections, sources_for_sites
from .search.preview_urls import artwork_preview_url
from .search.source_health import test_sources
from .settings import load_settings, save_settings
from .search.env_keys import (
    SIGNUP_URL,
    set_smithsonian_api_key,
    smithsonian_api_key,
    smithsonian_api_key_hint,
)
from .search.thumbnails import (
    bytes_to_photo,
    fetch_thumbnail_bytes,
    get_cached_bytes,
    prefetch_urls,
)
from .search.types import ArtworkHit, SortMode
from .source_checkboxes import mount_scrollable_source_list, refresh_source_list_scroll
from .storage import SiteStore

_SORT_LABELS: dict[str, SortMode] = {
    "Trafnosc": "score",
    "Zrodlo": "source",
    "Artysta": "artist",
    "Tytul": "title",
}


def _show_smithsonian_key_dialog(parent: tk.Misc, *, on_saved: Callable[[], None] | None = None) -> None:
    win = tk.Toplevel(parent)
    win.title("Smithsonian API — klucz")
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)
    position_toplevel_screen_center(win, 540, 300)

    frame = ttk.Frame(win, padding=14)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text="Klucz Smithsonian Open Access (SMITHSONIAN_API_KEY)",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")

    current = smithsonian_api_key()
    if current:
        ttk.Label(
            frame,
            text=f"Aktualny klucz: {smithsonian_api_key_hint()}",
            foreground="#666",
        ).pack(anchor="w", pady=(4, 0))

    ttk.Label(
        frame,
        text=(
            "Wklej klucz z api.data.gov (darmowa rejestracja). "
            "Zostanie zapisany w cursor-api/.env jako SMITHSONIAN_API_KEY."
        ),
        wraplength=480,
        justify="left",
    ).pack(fill="x", pady=(8, 6))

    link_row = ttk.Frame(frame)
    link_row.pack(fill="x", pady=(0, 8))
    ttk.Label(link_row, text="Zarejestruj klucz: ").pack(side="left")
    link = tk.Label(
        link_row,
        text=SIGNUP_URL,
        fg="#06a",
        cursor="hand2",
        font=("Segoe UI", 9, "underline"),
    )
    link.pack(side="left")
    link.bind("<Button-1>", lambda _e: webbrowser.open(SIGNUP_URL))

    ttk.Label(frame, text="SMITHSONIAN_API_KEY:").pack(anchor="w")
    key_var = tk.StringVar(value=current)
    entry = ttk.Entry(frame, textvariable=key_var, width=60, show="*")
    entry.pack(fill="x", pady=(2, 4))
    show_var = tk.IntVar(value=0)

    def _toggle_show() -> None:
        entry.configure(show="" if show_var.get() else "*")

    ttk.Checkbutton(frame, text="Pokaz znaki", variable=show_var, command=_toggle_show).pack(
        anchor="w",
    )

    status_var = tk.StringVar(value="")
    ttk.Label(frame, textvariable=status_var, foreground="#a60", wraplength=480).pack(
        fill="x",
        pady=(4, 0),
    )

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(12, 0))

    def _close() -> None:
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    def _save() -> None:
        new_key = key_var.get().strip()
        if len(new_key) < 8:
            status_var.set("Klucz wyglada na za krotki. Sprawdz i sprobuj ponownie.")
            return
        try:
            env_path = set_smithsonian_api_key(new_key)
        except (OSError, ValueError) as exc:
            status_var.set(str(exc))
            return
        show_toast(
            parent,
            f"Zapisano SMITHSONIAN_API_KEY ({env_path.name})",
            duration_ms=1800,
        )
        if on_saved:
            on_saved()
        _close()

    ttk.Button(btn_row, text="Anuluj", command=_close).pack(side="right")
    ttk.Button(btn_row, text="Zapisz", command=_save).pack(side="right", padx=(0, 8))
    entry.focus_set()
    win.bind("<Escape>", lambda _e: _close())


def build_search_tab(parent: tk.Misc, root: tk.Misc, *, get_store: Callable[[], SiteStore]) -> None:
    state: dict[str, object] = {"running": False, "hits": [], "agg": None}
    app_settings = load_settings()

    top = ttk.Frame(parent, padding=(12, 10, 12, 6))
    top.pack(fill="x")
    ttk.Label(top, text="Silnik wyszukiwania", font=("Segoe UI", 13, "bold")).pack(side="left")

    key_row = ttk.Frame(parent, padding=(12, 0, 12, 4))
    key_row.pack(fill="x")
    key_label = ttk.Label(key_row, text="SMITHSONIAN_API_KEY: …")
    key_label.pack(side="left")

    def _update_key_label() -> None:
        if smithsonian_api_key():
            key_label.configure(
                text=f"SMITHSONIAN_API_KEY: OK ({smithsonian_api_key_hint()}, cursor-api/.env)",
                foreground="#0a6",
            )
        else:
            key_label.configure(
                text="SMITHSONIAN_API_KEY: BRAK — wymagany do API Smithsonian",
                foreground="#a60",
            )

    ttk.Button(
        key_row,
        text="Klucz Smithsonian…",
        command=lambda: _show_smithsonian_key_dialog(root, on_saved=_update_key_label),
    ).pack(side="right")
    _update_key_label()

    form = ttk.Frame(parent, padding=(12, 0, 12, 8))
    form.pack(fill="x")

    artist_var = tk.StringVar()
    title_var = tk.StringVar()
    ttk.Label(form, text="Artysta:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    artist_entry = ttk.Entry(form, textvariable=artist_var, width=36)
    artist_entry.grid(row=0, column=1, sticky="w", pady=4)
    ttk.Label(form, text="Tytul obrazu:").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=4)
    title_entry = ttk.Entry(form, textvariable=title_var, width=36)
    title_entry.grid(row=0, column=3, sticky="w", pady=4)

    limit_var = tk.IntVar(value=app_settings.search_limit)
    ttk.Label(form, text="Limit / zrodlo:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
    limit_spin = ttk.Spinbox(form, from_=1, to=30, width=6, textvariable=limit_var)
    limit_spin.grid(row=1, column=1, sticky="w", pady=4)

    sort_var = tk.StringVar(value="Trafnosc")
    ttk.Label(form, text="Sortuj:").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=4)
    sort_combo = ttk.Combobox(
        form,
        textvariable=sort_var,
        values=list(_SORT_LABELS.keys()),
        state="readonly",
        width=14,
    )
    sort_combo.grid(row=1, column=3, sticky="w", pady=4)

    hint = ttk.Label(
        parent,
        text=(
            "Przeszukuje API / lokalne zbiory CSV powiazane z Twoimi zakladkami "
            "(Met, Rijksmuseum, Cleveland, SMK, Mia, NGA, Walters…). "
            "Gdy brak API — link do wyszukiwania w przegladarce."
        ),
        wraplength=920,
        foreground="#555",
        padding=(12, 0, 12, 8),
    )
    hint.pack(fill="x")

    src_frame = ttk.LabelFrame(parent, text="Zrodla (z zakladek)", padding=(8, 6))
    src_frame.pack(fill="x", padx=12, pady=(0, 8))

    src_vars: dict[str, tk.BooleanVar] = {}
    src_inner = mount_scrollable_source_list(src_frame, height=120)

    def _persist_settings() -> None:
        nonlocal app_settings
        try:
            lim = int(limit_var.get())
        except tk.TclError:
            lim = app_settings.search_limit
        app_settings.search_limit = max(1, min(30, lim))
        app_settings.source_checked = {sid: var.get() for sid, var in src_vars.items()}
        save_settings(app_settings)

    def _refresh_sources() -> None:
        prev = {sid: var.get() for sid, var in src_vars.items()}
        saved_checked = app_settings.source_checked
        for child in src_inner.winfo_children():
            child.destroy()
        src_vars.clear()
        store: SiteStore = get_store()
        detected = sources_for_sites(store.sorted())
        if not detected:
            ttk.Label(
                src_inner,
                text="Dodaj linki muzeow w zakladce «Zakladki», aby wlaczyc wyszukiwanie.",
                foreground="#a60",
            ).pack(anchor="w")
            return
        for idx, src in enumerate(detected):
            default = prev.get(src.source_id, saved_checked.get(src.source_id, True))
            var = tk.BooleanVar(value=default)
            var.trace_add("write", lambda *_a: _persist_settings())
            src_vars[src.source_id] = var
            badges = []
            if src.api:
                badges.append("API")
            if src.local:
                badges.append("CSV")
            if not src.api:
                badges.append("WWW")
            label = f"{src.name} ({', '.join(badges)})"
            ttk.Checkbutton(src_inner, text=label, variable=var).grid(
                row=idx // 2,
                column=idx % 2,
                sticky="w",
                padx=(0, 16),
                pady=2,
            )
        refresh_source_list_scroll(src_inner)

    btn_row = ttk.Frame(parent, padding=(12, 0, 12, 6))
    btn_row.pack(fill="x")
    search_btn = ttk.Button(btn_row, text="Szukaj we wszystkich zrodłach")
    search_btn.pack(side="left")
    stop_btn = ttk.Button(btn_row, text="Stop", state="disabled")
    stop_btn.pack(side="left", padx=(8, 0))
    download_btn = ttk.Button(btn_row, text="Pobierz obraz (HD)")
    download_btn.pack(side="left", padx=(8, 0))
    open_link_btn = ttk.Button(btn_row, text="Otworz link")
    open_link_btn.pack(side="left", padx=(8, 0))
    batch_btn = ttk.Button(btn_row, text="Pobierz zaznaczone")
    batch_btn.pack(side="left", padx=(8, 0))
    test_btn = ttk.Button(btn_row, text="Test zrodel")
    test_btn.pack(side="left", padx=(8, 0))
    status_var = tk.StringVar(value="Gotowy.")
    ttk.Label(btn_row, textvariable=status_var, foreground="#444").pack(side="right")

    outer = ttk.Frame(parent, padding=(12, 0, 12, 6))
    outer.pack(fill="both", expand=True)
    paned = ttk.Panedwindow(outer, orient="horizontal")
    paned.pack(fill="both", expand=True)

    left_col = ttk.Frame(paned)
    paned.add(left_col, weight=3)

    results_frame = ttk.LabelFrame(left_col, text="Wyniki", padding=(8, 6))
    results_frame.pack(fill="both", expand=True)

    preview_frame = ttk.LabelFrame(paned, text="Podglad", padding=(8, 6))
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

    err_frame = ttk.LabelFrame(left_col, text="Problemy ze zrodlami", padding=(8, 4))
    err_frame.pack(fill="x", pady=(8, 0))
    err_list = tk.Listbox(err_frame, height=3, font=("Segoe UI", 9), fg="#a60")
    err_scroll = ttk.Scrollbar(err_frame, orient="vertical", command=err_list.yview)
    err_list.configure(yscrollcommand=err_scroll.set)
    err_list.pack(side="left", fill="both", expand=True)
    err_scroll.pack(side="right", fill="y")

    cols = ("source", "artist", "title", "date", "mode", "url")
    tree = ttk.Treeview(results_frame, columns=cols, show="headings", selectmode="extended")
    tree.heading("source", text="Zrodlo")
    tree.heading("artist", text="Artysta")
    tree.heading("title", text="Tytul")
    tree.heading("date", text="Data")
    tree.heading("mode", text="Typ")
    tree.heading("url", text="URL")
    tree.column("source", width=160, stretch=False)
    tree.column("artist", width=150, stretch=True)
    tree.column("title", width=220, stretch=True)
    tree.column("date", width=90, stretch=False)
    tree.column("mode", width=50, stretch=False)
    tree.column("url", width=280, stretch=True)
    scroll = ttk.Scrollbar(results_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    tree.tag_configure("web", foreground="#7070a0")
    tree.tag_configure("api", foreground="#1a1a1a")
    tree.tag_configure("local", foreground="#1a1a1a")

    cancel_event = threading.Event()
    preview_token = {"n": 0}
    download_cancel = threading.Event()
    download_state = {"running": False}

    def _current_sort() -> SortMode:
        return _SORT_LABELS.get(sort_var.get(), "score")

    def _fill_errors(agg) -> None:
        err_list.delete(0, "end")
        if agg is None:
            return
        for block in agg.results:
            if block.error and not block.hits:
                err_list.insert("end", block.error)
            elif block.error and block.hits:
                err_list.insert("end", f"{block.error} (czesciowe wyniki: {len(block.hits)})")

    def _fill_results(hits: list[ArtworkHit]) -> None:
        tree.delete(*tree.get_children())
        state["hits"] = hits
        for idx, hit in enumerate(hits):
            mode_label = hit.search_mode.upper()
            if hit.search_mode == "web":
                mode_label = "WWW"
            tags = (hit.search_mode,)
            tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    hit.source_name,
                    hit.artist,
                    hit.title,
                    hit.date,
                    mode_label,
                    hit.object_url,
                ),
                tags=tags,
            )
        if hits:
            tree.selection_set("0")
            tree.focus("0")
            _show_preview_for_index(0)

            def _prefetch_first() -> None:
                urls = [artwork_preview_url(h) for h in hits[:5] if artwork_preview_url(h)]
                if urls:
                    prefetch_urls(urls)

            threading.Thread(
                target=_prefetch_first,
                daemon=True,
                name="stronyzobrazami-prefetch",
            ).start()
        else:
            _clear_preview()

    def _apply_photo(photo, *, token: int) -> None:
        if preview_token["n"] != token:
            return
        preview_label.configure(image=photo, text="", bg="#ffffff")
        preview_label._thumb_photo = photo  # type: ignore[attr-defined]

    def _show_preview_error(msg: str, *, token: int) -> None:
        if preview_token["n"] != token:
            return
        preview_label.configure(image="", text=msg, bg="#fff3e0", fg="#a60")
        preview_label._thumb_photo = None  # type: ignore[attr-defined]

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
        preview_label.configure(image="", text="Laduje miniaturke...", bg="#f4f4f4", fg="#666")

        def work() -> None:
            preview_url = artwork_preview_url(hit)
            if not preview_url:

                def no_image() -> None:
                    if preview_token["n"] != token:
                        return
                    preview_label.configure(
                        image="",
                        text="Brak miniatury\n(API nie podalo obrazu)",
                        bg="#f4f4f4",
                        fg="#888",
                    )
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
                    except (ImportError, OSError, ValueError) as exc:
                        _show_preview_error(f"Miniatura:\n{exc}", token=token)
                        return
                    _apply_photo(photo, token=token)

                root.after(0, show_cached)
                return

            raw = fetch_thumbnail_bytes(preview_url)
            if raw is None:
                root.after(
                    0,
                    lambda t=token: _show_preview_error("Nie udalo sie pobrac\nminiatury.", token=t),
                )
                return

            def ok() -> None:
                if preview_token["n"] != token:
                    return
                try:
                    photo = bytes_to_photo(raw)
                except (ImportError, OSError, ValueError) as exc:
                    _show_preview_error(f"Miniatura:\n{exc}", token=token)
                    return
                _apply_photo(photo, token=token)

            root.after(0, ok)

        threading.Thread(target=work, daemon=True, name="stronyzobrazami-thumb").start()

    def _on_tree_select(_event: tk.Event | None = None) -> None:
        sel = tree.selection()
        if not sel:
            return
        try:
            _show_preview_for_index(int(sel[0]))
        except ValueError:
            pass

    tree.bind("<<TreeviewSelect>>", _on_tree_select)

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

    def _open_link_on_url_click(event: tk.Event) -> None:
        if tree.identify_region(event.x, event.y) != "cell":
            return
        if tree.identify_column(event.x) != "#6":
            return
        iid = tree.identify_row(event.y)
        if not iid:
            return
        hits_list: list[ArtworkHit] = state.get("hits") or []
        try:
            row_hit = hits_list[int(iid)]
        except (IndexError, ValueError):
            return
        if row_hit.object_url:
            webbrowser.open(row_hit.object_url)

    tree.bind("<ButtonRelease-1>", _open_link_on_url_click, add="+")
    open_link_btn.configure(command=lambda: _open_hit())

    def _selected_hits() -> list[ArtworkHit]:
        hits: list[ArtworkHit] = state.get("hits") or []
        out: list[ArtworkHit] = []
        for iid in tree.selection():
            try:
                out.append(hits[int(iid)])
            except (IndexError, ValueError):
                continue
        return out

    def _download_selected() -> None:
        if download_state["running"]:
            return
        selected = _selected_hits()
        if not selected:
            messagebox.showinfo("Pobierz obraz", "Zaznacz wiersz z wynikiem.", parent=root)
            return
        if len(selected) > 1:
            messagebox.showinfo(
                "Pobierz obraz",
                "Zaznaczono wiele wierszy — uzyj «Pobierz zaznaczone».",
                parent=root,
            )
            return
        from .download_gui import run_download_for_hit

        hit = selected[0]
        download_cancel.clear()
        download_state["running"] = True
        download_btn.configure(state="disabled")
        status_var.set("Pobieranie obrazu…")

        def _done_download() -> None:
            download_state["running"] = False
            download_btn.configure(state="normal")

        run_download_for_hit(
            root,
            hit,
            log=lambda msg: root.after(0, lambda m=msg: status_var.set(m)),
            cancel_event=download_cancel,
            on_done=_done_download,
        )

    download_btn.configure(command=_download_selected)

    def _download_batch() -> None:
        if download_state["running"]:
            return
        selected = _selected_hits()
        if not selected:
            messagebox.showinfo("Pobierz zaznaczone", "Zaznacz co najmniej jeden wiersz.", parent=root)
            return
        from tkinter import filedialog

        from .batch_download import run_batch_download

        initial = app_settings.download_dir or str(Path.home() / "Downloads")
        dest = filedialog.askdirectory(parent=root, title="Katalog na pobrane obrazy", initialdir=initial)
        if not dest:
            return
        app_settings.download_dir = dest
        save_settings(app_settings)
        download_cancel.clear()
        download_state["running"] = True
        download_btn.configure(state="disabled")
        batch_btn.configure(state="disabled")
        status_var.set(f"Pobieranie {len(selected)} obrazow…")

        def _done_batch() -> None:
            download_state["running"] = False
            download_btn.configure(state="normal")
            batch_btn.configure(state="normal")

        run_batch_download(
            root,
            selected,
            Path(dest),
            workers=app_settings.iiif_workers,
            force_png=app_settings.force_png,
            log=lambda msg: root.after(0, lambda m=msg: status_var.set(m)),
            cancel_event=download_cancel,
            on_done=_done_batch,
        )

    batch_btn.configure(command=_download_batch)

    def _test_sources() -> None:
        selected_ids = _selected_source_ids()
        store = get_store()
        detected = sources_for_sites(store.sorted())
        if selected_ids:
            wanted = set(selected_ids)
            detected = [s for s in detected if s.source_id in wanted]
        if not detected:
            messagebox.showinfo("Test zrodel", "Brak zrodel do testu.", parent=root)
            return
        test_btn.configure(state="disabled")
        status_var.set("Testuje zrodla…")

        def work() -> None:
            rows = test_sources(detected)
            lines = [f"{'OK' if ok else 'BLAD'} — {name}: {msg}" for name, ok, msg in rows]

            def ui() -> None:
                err_list.delete(0, "end")
                for line in lines:
                    err_list.insert("end", line)
                ok_n = sum(1 for _n, ok, _m in rows if ok)
                status_var.set(f"Test zrodel: {ok_n}/{len(rows)} OK")
                test_btn.configure(state="normal")

            root.after(0, ui)

        threading.Thread(target=work, daemon=True, name="stronyzobrazami-test").start()

    test_btn.configure(command=_test_sources)

    def _selected_source_ids() -> list[str]:
        return [sid for sid, var in src_vars.items() if var.get()]

    def _apply_sort_from_state() -> None:
        agg = state.get("agg")
        if agg is None:
            return
        hits = agg.sorted_hits(_current_sort())
        _fill_results(hits)

    def _run_search() -> None:
        artist = artist_var.get().strip()
        title = title_var.get().strip()
        if not artist and not title:
            messagebox.showinfo("Wyszukiwanie", "Podaj artyste i/lub tytul.", parent=root)
            return
        selected = _selected_source_ids()
        if not selected:
            messagebox.showinfo(
                "Wyszukiwanie",
                "Zaznacz co najmniej jedno zrodlo (lub dodaj zakladki muzeow).",
                parent=root,
            )
            return
        try:
            limit = int(limit_var.get())
        except tk.TclError:
            limit = 10
        limit = max(1, min(30, limit))
        limit_var.set(limit)
        _persist_settings()

        cancel_event.clear()
        state["running"] = True
        search_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        status_var.set("Szukam...")
        tree.delete(*tree.get_children())
        err_list.delete(0, "end")
        _clear_preview()

        def work() -> None:
            def _status(msg: str) -> None:
                if cancel_event.is_set():
                    return
                root.after(0, lambda m=msg: status_var.set(m))

            try:
                agg = search_collections(
                    artist=artist,
                    title=title,
                    sites=get_store().sorted(),
                    source_ids=selected,
                    limit_per_source=limit,
                    on_status=_status,
                    cancel_event=cancel_event,
                )
            except Exception as exc:
                root.after(
                    0,
                    lambda e=exc: (
                        status_var.set(f"Blad: {e}"),
                        messagebox.showerror("Wyszukiwanie", str(e), parent=root),
                    ),
                )
                root.after(0, _done)
                return

            hits = agg.sorted_hits(_current_sort())
            err_sources = agg.sources_with_errors

            def _ui() -> None:
                state["agg"] = agg
                _fill_results(hits)
                _fill_errors(agg)
                if agg.cancelled:
                    msg = f"Anulowano — czesciowe wyniki: {len(hits)}."
                else:
                    msg = f"Znaleziono {len(hits)} wynik(ow) w {len(agg.results)} zrodle(ach)."
                if err_sources:
                    msg += f" Problemy: {len(err_sources)} zrodlo(a)."
                status_var.set(msg)
                show_toast(root, msg, duration_ms=2200)

            root.after(0, _ui)
            root.after(0, _done)

        def _done() -> None:
            state["running"] = False
            search_btn.configure(state="normal")
            stop_btn.configure(state="disabled")

        threading.Thread(target=work, daemon=True, name="stronyzobrazami-search").start()

    def _stop() -> None:
        cancel_event.set()
        status_var.set("Anulowanie...")

    sort_combo.bind("<<ComboboxSelected>>", lambda _e: _apply_sort_from_state())

    search_btn.configure(command=_run_search)
    stop_btn.configure(command=_stop)
    artist_entry.bind("<Return>", lambda _e: _run_search())
    title_entry.bind("<Return>", lambda _e: _run_search())

    _refresh_sources()
    parent.bind("<Visibility>", lambda _e: _refresh_sources(), add="+")

    # Eksportuj odswiezanie przy zmianie zakladek
    parent._refresh_search_sources = _refresh_sources  # type: ignore[attr-defined]
