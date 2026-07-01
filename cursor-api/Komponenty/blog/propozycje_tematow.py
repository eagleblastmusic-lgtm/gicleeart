"""Sub-view 'Propozycje tematow' - lista zapisanych propozycji + menu PPM.

Funkcjonalnosci PPM:
- Kopiuj temat (autokopiowanie do schowka)
- Generuj tresc (otwiera Generator tresci z wpisanym tematem)
- Oznacz jako wykorzystany / nie wykorzystany
- Usun
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from Komponenty._shared.toast import show_toast

from . import storage

_BG = "#f4f4f7"


def build_topics_screen(
    parent: tk.Widget,
    *,
    on_back: Callable[[], None],
    on_generate_content: Callable[[str, str], None],
) -> tk.Widget:
    """Zwraca gotowy frame z lista propozycji tematow."""
    outer = tk.Frame(parent, bg=_BG)

    # Toolbar
    toolbar = tk.Frame(outer, bg=_BG)
    toolbar.pack(fill="x", padx=14, pady=(12, 4))
    ttk.Button(toolbar, text="< Blog", command=on_back).pack(side="left")
    tk.Label(
        toolbar, text="Propozycje tematow", bg=_BG,
        font=("Segoe UI", 18, "bold"), fg="#222",
    ).pack(side="left", padx=(14, 0))
    tk.Label(
        toolbar, text="PPM na tytul -> akcje (kopiuj, generuj tresc, usun)",
        bg=_BG, fg="#666", font=("Segoe UI", 10),
    ).pack(side="left", padx=(10, 0), pady=(8, 0))

    action_row = tk.Frame(outer, bg=_BG)
    action_row.pack(fill="x", padx=14, pady=(4, 6))
    refresh_btn = ttk.Button(action_row, text="🔄 Odswiez")
    refresh_btn.pack(side="left")
    count_var = tk.StringVar(value="")
    tk.Label(action_row, textvariable=count_var, bg=_BG, fg="#555").pack(side="left", padx=(12, 0))

    # Tree w kontenerze
    body = tk.Frame(outer, bg=_BG)
    body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

    columns = ("status", "title", "reason", "keywords")
    tree = ttk.Treeview(body, columns=columns, show="headings", selectmode="browse")
    tree.heading("status", text="")
    tree.heading("title", text="Tytul propozycji")
    tree.heading("reason", text="Uzasadnienie")
    tree.heading("keywords", text="Keywords")
    tree.column("status", width=30, anchor="center", stretch=False)
    tree.column("title", width=380, anchor="w")
    tree.column("reason", width=360, anchor="w")
    tree.column("keywords", width=240, anchor="w")

    vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    tree.tag_configure("used", foreground="#888", font=("Segoe UI", 10, "overstrike"))
    tree.tag_configure("fresh", foreground="#222")

    # mapa iid -> TopicProposal
    row_map: dict[str, storage.TopicProposal] = {}

    # Context menu
    menu = tk.Menu(tree, tearoff=0)

    def _selected_topic() -> storage.TopicProposal | None:
        sel = tree.selection()
        if not sel:
            return None
        return row_map.get(sel[0])

    def _copy_title() -> None:
        t = _selected_topic()
        if not t:
            return
        try:
            tree.clipboard_clear()
            tree.clipboard_append(t.title)
            tree.update()
        except tk.TclError:
            return
        show_toast(tree, "Skopiowano temat", duration_ms=1000)

    def _copy_full() -> None:
        t = _selected_topic()
        if not t:
            return
        payload = t.title
        if t.reason:
            payload += f"\n\nUzasadnienie: {t.reason}"
        if t.keywords:
            payload += f"\nKeywords: {', '.join(t.keywords)}"
        try:
            tree.clipboard_clear()
            tree.clipboard_append(payload)
            tree.update()
        except tk.TclError:
            return
        show_toast(tree, "Skopiowano caly temat", duration_ms=1000)

    def _generate() -> None:
        t = _selected_topic()
        if not t:
            return
        on_generate_content(t.title, t.id)

    def _toggle_used() -> None:
        t = _selected_topic()
        if not t:
            return
        storage.mark_topic_used(t.id, not t.used)
        _reload()

    def _delete() -> None:
        t = _selected_topic()
        if not t:
            return
        if not messagebox.askyesno("Usunac?", f"Usunac propozycje:\n\n{t.title}?"):
            return
        storage.remove_topic(t.id)
        _reload()

    menu.add_command(label="📋 Kopiuj temat", command=_copy_title)
    menu.add_command(label="📋 Kopiuj temat + uzasadnienie", command=_copy_full)
    menu.add_separator()
    menu.add_command(label="✍️ Generuj tresc posta", command=_generate)
    menu.add_separator()
    menu.add_command(label="✓ Oznacz (nie)wykorzystany", command=_toggle_used)
    menu.add_command(label="🗑 Usun", command=_delete)

    def _on_right_click(evt: tk.Event) -> None:
        iid = tree.identify_row(evt.y)
        if iid:
            tree.selection_set(iid)
            tree.focus(iid)
        try:
            menu.tk_popup(evt.x_root, evt.y_root)
        finally:
            menu.grab_release()

    def _on_double_click(_evt: tk.Event) -> None:
        _generate()

    tree.bind("<Button-3>", _on_right_click)  # PPM Windows/Linux
    tree.bind("<Button-2>", _on_right_click)  # PPM macOS (w niektorych konfiguracjach)
    tree.bind("<Double-Button-1>", _on_double_click)

    def _reload() -> None:
        tree.delete(*tree.get_children())
        row_map.clear()
        topics = storage.load_topics()
        for t in topics:
            iid = t.id
            row_map[iid] = t
            tag = "used" if t.used else "fresh"
            status = "✓" if t.used else "•"
            tree.insert(
                "", "end", iid=iid,
                values=(status, t.title, t.reason, ", ".join(t.keywords)),
                tags=(tag,),
            )
        used_n = sum(1 for t in topics if t.used)
        count_var.set(f"Propozycji: {len(topics)}  |  wykorzystane: {used_n}")

    refresh_btn.configure(command=_reload)
    _reload()

    return outer
