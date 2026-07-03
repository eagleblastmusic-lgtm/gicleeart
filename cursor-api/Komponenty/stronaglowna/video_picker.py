"""Dialog wyboru filmu z Shopify Files."""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .service import (
    VIDEO_SUFFIXES,
    delete_shopify_video,
    list_shopify_videos,
    rename_shopify_video,
)


def _format_created_at(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text[:16]


def _selected_row(tree: ttk.Treeview, rows: list[dict[str, str]]) -> tuple[int, dict[str, str]] | None:
    sel = tree.selection()
    if not sel:
        return None
    try:
        idx = int(sel[0])
        return idx, rows[idx]
    except (IndexError, KeyError, ValueError):
        return None


def pick_shopify_video(
    parent: tk.Misc,
    *,
    title: str = "Filmy w Shopify Files",
) -> str | None:
    """Otwiera listę wgranych filmów; zwraca shopify://files/videos/… lub None."""
    win = tk.Toplevel(parent)
    win.title(title)
    position_toplevel_screen_center(win, 820, 560)
    win.transient(parent.winfo_toplevel())
    win.grab_set()

    choice: dict[str, str | None] = {"ref": None}
    rows: list[dict[str, str]] = []

    top = ttk.Frame(win, padding=(12, 10))
    top.pack(fill="x")
    ttk.Label(
        top,
        text="Filmy w Shopify Files (najnowsze u góry). Dwuklik = podgląd.",
        font=("", 10, "bold"),
    ).pack(anchor="w")

    filter_row = ttk.Frame(top)
    filter_row.pack(fill="x", pady=(8, 0))
    filter_var = tk.StringVar(value="")
    ttk.Label(filter_row, text="Szukaj:").pack(side="left")
    filter_entry = ttk.Entry(filter_row, textvariable=filter_var, width=36)
    filter_entry.pack(side="left", padx=(6, 8))
    status_var = tk.StringVar(value="Ładowanie listy filmów…")
    ttk.Label(filter_row, textvariable=status_var, foreground="#666").pack(side="left")

    table_frame = ttk.Frame(win, padding=(12, 0))
    table_frame.pack(fill="both", expand=True)
    cols = ("filename", "created")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=16, selectmode="browse")
    tree.heading("filename", text="Plik")
    tree.heading("created", text="Data wgrania")
    tree.column("filename", width=560, anchor="w", stretch=True)
    tree.column("created", width=140, anchor="w")
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def _populate(items: list[dict[str, str]]) -> None:
        nonlocal rows
        rows = list(items)
        tree.delete(*tree.get_children())
        for i, row in enumerate(rows):
            tree.insert(
                "",
                "end",
                iid=str(i),
                values=(row.get("label") or row.get("filename") or "", _format_created_at(row.get("created_at", ""))),
            )
        status_var.set(f"Znaleziono: {len(rows)} filmów.")

    def _load(*, search: str = "") -> None:
        status_var.set("Ładowanie…")
        tree.delete(*tree.get_children())

        def worker() -> None:
            try:
                items = list_shopify_videos(search=search)
            except Exception as exc:
                err = str(exc)
                win.after(0, lambda: (status_var.set("Błąd listy filmów."), messagebox.showerror(title, err, parent=win)))
                return

            win.after(0, lambda: _populate(items))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh() -> None:
        _load(search=filter_var.get())

    def _choose(_evt: object = None) -> None:
        picked = _selected_row(tree, rows)
        if not picked:
            return
        choice["ref"] = picked[1]["ref"]
        win.destroy()

    def _preview(_evt: object = None) -> None:
        picked = _selected_row(tree, rows)
        if not picked:
            return
        from .video_preview import preview_shopify_video

        preview_shopify_video(win, picked[1]["ref"], title="Podgląd filmu")

    def _rename() -> None:
        picked = _selected_row(tree, rows)
        if not picked:
            messagebox.showinfo(title, "Wybierz film z listy.", parent=win)
            return
        idx, row = picked
        filename = str(row.get("filename") or row.get("label") or "")
        ext = Path(filename).suffix.lower()
        if ext not in VIDEO_SUFFIXES:
            ext = ".mp4"
        initial = Path(filename).stem if filename else ""
        new_name = simpledialog.askstring(
            "Zmień nazwę",
            f"Nowa nazwa pliku (zostanie rozszerzenie {ext}):\n\n"
            "Uwaga: odwołania w motywie używają starej nazwy — po zmianie nazwy pliku "
            "trzeba je zaktualizować w hero/kolażu.",
            initialvalue=initial,
            parent=win,
        )
        if not new_name:
            return
        status_var.set("Zmieniam nazwę…")

        def worker() -> None:
            try:
                result = rename_shopify_video(
                    row["ref"],
                    new_name,
                    gid=str(row.get("gid") or ""),
                )
            except Exception as exc:
                win.after(
                    0,
                    lambda: (
                        status_var.set("Błąd zmiany nazwy."),
                        messagebox.showerror(title, str(exc), parent=win),
                    ),
                )
                return

            def done() -> None:
                rows[idx].update(
                    {
                        "ref": result["ref"],
                        "filename": result["filename"],
                        "label": result["label"],
                    }
                )
                tree.item(str(idx), values=(result["label"], _format_created_at(rows[idx].get("created_at", ""))))
                status_var.set(f"Zaktualizowano: {result['label']}")
                note = str(result.get("note") or "").strip()
                if note:
                    messagebox.showinfo(title, note, parent=win)

            win.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _delete() -> None:
        picked = _selected_row(tree, rows)
        if not picked:
            messagebox.showinfo(title, "Wybierz film z listy.", parent=win)
            return
        idx, row = picked
        label = row.get("label") or row.get("filename") or row.get("ref")
        if not messagebox.askyesno(
            title,
            f"Usunąć plik z Shopify Files?\n\n{label}\n\n"
            "Odwołania w motywie (hero, kolaż) przestaną działać, dopóki nie wgrasz pliku ponownie "
            "lub nie wybierzesz innego filmu.",
            parent=win,
        ):
            return
        status_var.set("Usuwam plik…")

        def worker() -> None:
            try:
                delete_shopify_video(row["ref"], gid=str(row.get("gid") or ""))
            except Exception as exc:
                win.after(
                    0,
                    lambda: (
                        status_var.set("Błąd usuwania."),
                        messagebox.showerror(title, str(exc), parent=win),
                    ),
                )
                return

            def done() -> None:
                rows.pop(idx)
                _populate(rows)
                status_var.set("Plik usunięty.")

            win.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    refresh_btn = ttk.Button(filter_row, text="Odśwież", command=_refresh)
    refresh_btn.pack(side="right")

    btns = ttk.Frame(win, padding=(12, 10))
    btns.pack(fill="x")
    ttk.Label(btns, text="Dwuklik = podgląd", foreground="#777").pack(side="left")
    ttk.Button(btns, text="Usuń", command=_delete).pack(side="left", padx=(12, 0))
    ttk.Button(btns, text="Zmień nazwę…", command=_rename).pack(side="left", padx=(8, 0))
    ttk.Button(btns, text="Anuluj", command=win.destroy).pack(side="right")
    ttk.Button(btns, text="Wybierz", command=_choose).pack(side="right", padx=(0, 8))

    tree.bind("<Double-1>", _preview)
    filter_entry.bind("<Return>", lambda _e: _refresh())
    win.after(80, _refresh)
    filter_entry.focus_set()

    parent.wait_window(win)
    return choice["ref"]
