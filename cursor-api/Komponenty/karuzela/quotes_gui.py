"""GUI: Cytaty — wiele cytatów per kolekcja Shopify (losowy w storefront)."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .quotes_service import (
    load_cached_collection_rows,
    load_collections_with_quotes,
    normalize_quotes,
    save_collection_quotes,
)

APP_TITLE = "Karuzela — Cytaty kolekcji"


def build_quotes_panel(parent: tk.Misc, *, on_back: Callable[[], None] | None = None) -> None:
    """Panel cytatów w istniejącym kontenerze (np. przejście z głównego okna Karuzeli)."""
    _build_ui(parent, on_back=on_back)


def open_quotes_window(parent: tk.Misc | None = None) -> None:
    host = tk.Toplevel(parent) if parent else tk.Tk()
    host.title(APP_TITLE)
    position_toplevel_screen_center(host, 1120, 740)
    host.minsize(900, 580)
    _build_ui(host, on_back=None)
    if not parent:
        host.mainloop()


def _build_ui(host: tk.Misc, *, on_back: Callable[[], None] | None) -> None:
    state: dict[str, Any] = {
        "rows": [],
        "selected": None,
        "editor_quotes": [],
        "selected_quote_idx": None,
        "_dirty": False,
    }

    intro = ttk.Frame(host, padding=(14, 12))
    intro.pack(fill="x")
    ttk.Label(
        intro,
        text="Przypisz cytaty do kolekcji autora.",
        font=("", 10, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        intro,
        text=(
            "Możesz dodać kilka cytatów — na stronie kolekcji wyświetli się jeden losowo "
            "(metafield custom.collection_quotes, storefront PUBLIC_READ)."
        ),
        wraplength=960,
        foreground="#555",
    ).pack(anchor="w", pady=(4, 0))

    body = ttk.Panedwindow(host, orient="horizontal")
    body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    left = ttk.LabelFrame(body, text="Kolekcje", padding=(8, 8))
    right = ttk.LabelFrame(body, text="Cytaty", padding=(10, 10))
    body.add(left, weight=3)
    body.add(right, weight=2)

    filter_var = tk.StringVar(value="")
    only_with_var = tk.BooleanVar(value=False)
    only_missing_var = tk.BooleanVar(value=False)
    progress_var = tk.StringVar(value="Ładowanie kolekcji z Shopify...")
    count_var = tk.StringVar(value="")
    selected_title_var = tk.StringVar(value="(wybierz kolekcję)")
    selected_handle_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="")

    filter_bar = ttk.Frame(left)
    filter_bar.pack(fill="x", pady=(0, 6))
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=28).pack(side="left", padx=(6, 8))
    ttk.Checkbutton(filter_bar, text="Tylko z cytatem", variable=only_with_var).pack(side="left", padx=4)
    ttk.Checkbutton(filter_bar, text="Tylko bez cytatu", variable=only_missing_var).pack(side="left", padx=4)
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="right")

    table_frame = ttk.Frame(left)
    table_frame.pack(fill="both", expand=True)
    cols = ("title", "handle", "status")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16, selectmode="browse")
    tree.heading("title", text="Kolekcja")
    tree.heading("handle", text="Handle")
    tree.heading("status", text="Cytaty")
    tree.column("title", width=260, anchor="w", stretch=True)
    tree.column("handle", width=180, anchor="w")
    tree.column("status", width=56, anchor="center")
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    ttk.Label(left, textvariable=progress_var, foreground="#666").pack(anchor="w", pady=(6, 0))

    ttk.Label(right, textvariable=selected_title_var, font=("", 11, "bold"), wraplength=380).pack(
        anchor="w"
    )
    ttk.Label(right, textvariable=selected_handle_var, foreground="#555").pack(anchor="w", pady=(2, 8))

    quotes_toolbar = ttk.Frame(right)
    quotes_toolbar.pack(fill="x", pady=(0, 6))
    add_btn = ttk.Button(quotes_toolbar, text="Dodaj cytat", state="disabled")
    add_btn.pack(side="left", padx=(0, 6))
    remove_btn = ttk.Button(quotes_toolbar, text="Usuń zaznaczony", state="disabled")
    remove_btn.pack(side="left")

    quotes_list_frame = ttk.Frame(right)
    quotes_list_frame.pack(fill="x", pady=(0, 8))
    quotes_list = tk.Listbox(quotes_list_frame, height=5, exportselection=False)
    quotes_list_scroll = ttk.Scrollbar(quotes_list_frame, orient="vertical", command=quotes_list.yview)
    quotes_list.configure(yscrollcommand=quotes_list_scroll.set)
    quotes_list.grid(row=0, column=0, sticky="nsew")
    quotes_list_scroll.grid(row=0, column=1, sticky="ns")
    quotes_list_frame.columnconfigure(0, weight=1)

    ttk.Label(right, text="Treść cytatu:").pack(anchor="w")
    quote_frame = ttk.Frame(right)
    quote_frame.pack(fill="both", expand=True, pady=(4, 8))
    quote_text = tk.Text(quote_frame, wrap="word", height=8, font=("", 10))
    quote_scroll = ttk.Scrollbar(quote_frame, orient="vertical", command=quote_text.yview)
    quote_text.configure(yscrollcommand=quote_scroll.set)
    quote_text.grid(row=0, column=0, sticky="nsew")
    quote_scroll.grid(row=0, column=1, sticky="ns")
    quote_frame.rowconfigure(0, weight=1)
    quote_frame.columnconfigure(0, weight=1)

    ttk.Label(right, textvariable=status_var, wraplength=380, foreground="#555").pack(anchor="w", pady=(0, 8))

    btn_row = ttk.Frame(right)
    btn_row.pack(fill="x", pady=(4, 0))
    save_btn = ttk.Button(btn_row, text="Zapisz cytaty", state="disabled")
    save_btn.pack(side="left", padx=(0, 6))
    clear_btn = ttk.Button(btn_row, text="Wyczyść wszystkie", state="disabled")
    clear_btn.pack(side="left", padx=(0, 6))
    open_btn = ttk.Button(btn_row, text="Otwórz kolekcję", state="disabled")
    open_btn.pack(side="left")

    bottom = ttk.Frame(host, padding=(12, 0, 12, 12))
    bottom.pack(fill="x")
    refresh_btn = ttk.Button(bottom, text="Odśwież listę", command=lambda: None)
    refresh_btn.pack(side="left")

    def _close_panel() -> None:
        if on_back:
            if _confirm_discard():
                on_back()
        else:
            top = host.winfo_toplevel()
            top.destroy()

    if on_back:
        ttk.Button(bottom, text="← Wróć", command=_close_panel).pack(side="right")
    else:
        ttk.Button(bottom, text="Zamknij", command=_close_panel).pack(side="right")

    row_by_iid: dict[str, dict[str, Any]] = {}
    _syncing_editor = {"active": False}

    def _set_buttons(enabled: bool) -> None:
        save_btn.configure(state="normal" if enabled else "disabled")
        clear_btn.configure(state="normal" if enabled else "disabled")
        open_btn.configure(state="normal" if enabled else "disabled")
        add_btn.configure(state="normal" if enabled else "disabled")
        remove_btn.configure(state="normal" if enabled else "disabled")

    def _quote_label(text: str, index: int) -> str:
        one_line = text.replace("\n", " ").strip()
        if len(one_line) > 64:
            one_line = one_line[:61] + "…"
        return f"{index + 1}. {one_line}" if one_line else f"{index + 1}. (pusty)"

    def _refresh_quotes_listbox(*, select_idx: int | None = None) -> None:
        quotes_list.delete(0, "end")
        for i, q in enumerate(state["editor_quotes"]):
            quotes_list.insert("end", _quote_label(q, i))
        if select_idx is not None and 0 <= select_idx < len(state["editor_quotes"]):
            quotes_list.selection_clear(0, "end")
            quotes_list.selection_set(select_idx)
            quotes_list.activate(select_idx)
            state["selected_quote_idx"] = select_idx
        elif state["editor_quotes"]:
            if state["selected_quote_idx"] is None:
                state["selected_quote_idx"] = 0
            idx = state["selected_quote_idx"]
            if 0 <= idx < len(state["editor_quotes"]):
                quotes_list.selection_set(idx)
                quotes_list.activate(idx)
        else:
            state["selected_quote_idx"] = None

    def _load_quote_into_editor(text: str) -> None:
        _syncing_editor["active"] = True
        quote_text.delete("1.0", "end")
        if text:
            quote_text.insert("1.0", text)
        _syncing_editor["active"] = False

    def _load_quotes_into_editor(quotes: list[str], *, select_idx: int | None = 0) -> None:
        state["editor_quotes"] = list(quotes)
        state["_dirty"] = False
        _refresh_quotes_listbox(select_idx=select_idx)
        idx = state["selected_quote_idx"]
        if idx is not None and 0 <= idx < len(state["editor_quotes"]):
            _load_quote_into_editor(state["editor_quotes"][idx])
        else:
            _load_quote_into_editor("")

    def _filtered_rows() -> list[dict[str, Any]]:
        q = (filter_var.get() or "").strip().lower()
        only_with = bool(only_with_var.get())
        only_missing = bool(only_missing_var.get())
        rows = list(state["rows"])
        out: list[dict[str, Any]] = []
        for r in rows:
            if only_with and not r.get("has_quote"):
                continue
            if only_missing and r.get("has_quote"):
                continue
            if q:
                blob = f"{r.get('title', '')} {r.get('handle', '')} {r.get('quote_preview', '')}".lower()
                if q not in blob:
                    continue
            out.append(r)
        return out

    def _refresh_tree(*, keep_handle: str | None = None) -> None:
        tree.delete(*tree.get_children())
        row_by_iid.clear()
        visible = _filtered_rows()
        count_var.set(f"{len(visible)} / {len(state['rows'])}")
        select_iid = None
        for r in visible:
            iid = tree.insert(
                "",
                "end",
                values=(r.get("title") or "", r.get("handle") or "", r.get("status") or "—"),
            )
            row_by_iid[iid] = r
            if keep_handle and r.get("handle") == keep_handle:
                select_iid = iid
        if select_iid:
            tree.selection_set(select_iid)
            tree.see(select_iid)
            _on_select()

    def _on_select(_evt=None) -> None:
        sel = tree.selection()
        if not sel:
            state["selected"] = None
            selected_title_var.set("(wybierz kolekcję)")
            selected_handle_var.set("")
            status_var.set("")
            _load_quotes_into_editor([])
            _set_buttons(False)
            return
        row = row_by_iid.get(sel[0])
        state["selected"] = row
        if not row:
            return
        selected_title_var.set(row.get("title") or row.get("handle") or "")
        selected_handle_var.set(f"Handle: {row.get('handle') or '—'}")
        quotes = normalize_quotes(row.get("quotes") or row.get("quote") or "")
        _load_quotes_into_editor(quotes, select_idx=0 if quotes else None)
        n = len(quotes)
        if n == 0:
            status_var.set("Brak cytatów — dodaj cytat i kliknij «Zapisz cytaty».")
        elif n == 1:
            status_var.set("1 cytat — na stronie zawsze ten sam.")
        else:
            status_var.set(f"{n} cytaty — na stronie losowo jeden z nich.")
        _set_buttons(True)

    def _on_quote_list_select(_evt=None) -> None:
        sel = quotes_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        state["selected_quote_idx"] = idx
        if 0 <= idx < len(state["editor_quotes"]):
            _load_quote_into_editor(state["editor_quotes"][idx])

    def _commit_editor_to_selected_quote() -> None:
        idx = state.get("selected_quote_idx")
        if idx is None or idx < 0 or idx >= len(state["editor_quotes"]):
            return
        state["editor_quotes"][idx] = quote_text.get("1.0", "end-1c").strip()

    def _mark_dirty(*_args) -> None:
        if _syncing_editor["active"]:
            return
        _commit_editor_to_selected_quote()
        state["_dirty"] = True
        idx = state.get("selected_quote_idx")
        if idx is not None and 0 <= idx < len(state["editor_quotes"]):
            _refresh_quotes_listbox(select_idx=idx)

    def _add_quote() -> None:
        _commit_editor_to_selected_quote()
        state["editor_quotes"].append("")
        state["_dirty"] = True
        new_idx = len(state["editor_quotes"]) - 1
        _refresh_quotes_listbox(select_idx=new_idx)
        _load_quote_into_editor("")
        quote_text.focus_set()

    def _remove_quote() -> None:
        idx = state.get("selected_quote_idx")
        if idx is None or idx < 0 or idx >= len(state["editor_quotes"]):
            return
        if not messagebox.askyesno(APP_TITLE, f"Usunąć cytat #{idx + 1}?", parent=host):
            return
        _commit_editor_to_selected_quote()
        del state["editor_quotes"][idx]
        state["_dirty"] = True
        next_idx = min(idx, len(state["editor_quotes"]) - 1) if state["editor_quotes"] else None
        _refresh_quotes_listbox(select_idx=next_idx)
        if next_idx is not None:
            _load_quote_into_editor(state["editor_quotes"][next_idx])
        else:
            _load_quote_into_editor("")

    quote_text.bind("<KeyRelease>", _mark_dirty)
    quotes_list.bind("<<ListboxSelect>>", _on_quote_list_select)
    tree.bind("<<TreeviewSelect>>", _on_select)

    def _confirm_discard() -> bool:
        if not state.get("_dirty"):
            return True
        return messagebox.askyesno(
            APP_TITLE,
            "Masz niezapisane zmiany cytatów. Kontynuować bez zapisu?",
            parent=host,
        )

    def _reload_async(*, keep_handle: str | None = None) -> None:
        if not _confirm_discard():
            return
        cached = load_cached_collection_rows()
        if cached:
            state["rows"] = cached
            _refresh_tree(keep_handle=keep_handle)
            progress_var.set(f"Cache: {len(cached)} kolekcji — odświeżam z Shopify…")
        else:
            progress_var.set("Pobieram kolekcje i metafieldy…")

        def worker() -> None:
            try:

                def on_progress(msg: str) -> None:
                    host.after(0, lambda m=msg: progress_var.set(m))

                rows = load_collections_with_quotes(on_progress=on_progress)

                def done() -> None:
                    state["rows"] = rows
                    progress_var.set(f"Załadowano {len(rows)} kolekcji.")
                    _refresh_tree(keep_handle=keep_handle)

                host.after(0, done)
            except Exception as exc:
                host.after(
                    0,
                    lambda: (
                        progress_var.set("Błąd ładowania."),
                        messagebox.showerror(APP_TITLE, str(exc), parent=host),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _save_quotes() -> None:
        row = state.get("selected")
        if not row:
            return
        _commit_editor_to_selected_quote()
        handle = str(row.get("handle") or "")
        quotes = normalize_quotes(state["editor_quotes"])
        save_btn.configure(state="disabled")
        progress_var.set(f"Zapisuję cytaty: {handle}…")

        def worker() -> None:
            result = save_collection_quotes(
                int(row.get("id") or 0),
                handle,
                str(row.get("title") or ""),
                quotes,
            )

            def done() -> None:
                save_btn.configure(state="normal")
                if not result.get("ok"):
                    progress_var.set("Błąd zapisu.")
                    messagebox.showerror(APP_TITLE, result.get("error") or "Nieznany błąd.", parent=host)
                    return
                saved = normalize_quotes(result.get("quotes") or [])
                preview = saved[0].replace("\n", " ").strip() if saved else ""
                if len(saved) > 1:
                    preview = f"{preview} (+{len(saved) - 1})"
                if len(preview) > 72:
                    preview = preview[:69] + "…"
                for r in state["rows"]:
                    if r.get("handle") == handle:
                        r["quotes"] = saved
                        r["quote"] = saved[0] if saved else ""
                        r["quote_preview"] = preview
                        r["has_quote"] = bool(saved)
                        r["quote_count"] = len(saved)
                        r["status"] = str(len(saved)) if saved else "—"
                        break
                state["_dirty"] = False
                _load_quotes_into_editor(saved, select_idx=0 if saved else None)
                progress_var.set(f"Zapisano {len(saved)} cytat(ów) dla {handle}.")
                if len(saved) == 0:
                    status_var.set("Cytaty usunięte.")
                elif len(saved) == 1:
                    status_var.set("1 cytat — na stronie zawsze ten sam.")
                else:
                    status_var.set(f"{len(saved)} cytaty — na stronie losowo jeden z nich.")
                show_toast(host, "Cytaty zapisane.")
                _refresh_tree(keep_handle=handle)

            host.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _clear_quotes() -> None:
        row = state.get("selected")
        if not row:
            return
        title = str(row.get("title") or row.get("handle") or "")
        if not messagebox.askyesno(APP_TITLE, f"Wyczyścić wszystkie cytaty dla «{title}»?", parent=host):
            return
        _load_quotes_into_editor([])
        state["_dirty"] = True
        _save_quotes()

    def _open_collection() -> None:
        row = state.get("selected")
        if not row:
            return
        handle = str(row.get("handle") or "").strip()
        if handle:
            webbrowser.open(f"https://giclee-art-3.myshopify.com/collections/{handle}")

    save_btn.configure(command=_save_quotes)
    clear_btn.configure(command=_clear_quotes)
    open_btn.configure(command=_open_collection)
    add_btn.configure(command=_add_quote)
    remove_btn.configure(command=_remove_quote)
    refresh_btn.configure(command=lambda: _reload_async())

    def _on_filter_change(*_args) -> None:
        if not _confirm_discard():
            return
        _refresh_tree(
            keep_handle=(state.get("selected") or {}).get("handle")
            if state.get("selected")
            else None
        )

    filter_var.trace_add("write", _on_filter_change)
    only_with_var.trace_add("write", _on_filter_change)
    only_missing_var.trace_add("write", _on_filter_change)

    if not on_back:
        host.protocol("WM_DELETE_WINDOW", _close_panel)

    _reload_async()
