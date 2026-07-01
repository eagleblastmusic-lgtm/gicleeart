"""Dialog Opcje — sekcje i widoczność kafelków."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from .component_loader import Component
from .launcher_layout import (
    DEFAULT_SECTIONS,
    LauncherLayout,
    TileLayoutEntry,
    build_default_layout,
    merge_layout,
    save_layout,
    section_titles,
)


def show_launcher_options(
    parent: tk.Widget,
    *,
    all_components: list[Component],
    normally_visible: set[str],
    layout: LauncherLayout,
    on_saved: Callable[[LauncherLayout], None],
) -> None:
    working = merge_layout(layout, all_components, normally_visible=normally_visible)
    section_names = section_titles(DEFAULT_SECTIONS)
    if working.section_order:
        for t in working.section_order:
            if t not in section_names:
                section_names.append(t)

    win = tk.Toplevel(parent)
    win.title("Opcje — układ kafelków")
    win.transient(parent.winfo_toplevel())
    win.grab_set()
    try:
        from Komponenty._shared.window_geometry import position_toplevel_screen_center
    except ImportError:
        position_toplevel_screen_center = None  # type: ignore[assignment]
    if position_toplevel_screen_center:
        position_toplevel_screen_center(win, 760, 620)
    else:
        win.geometry("760x620")

    hdr = ttk.Frame(win, padding=(12, 10))
    hdr.pack(fill="x")
    ttk.Label(
        hdr,
        text="Przypisz kafelki do sekcji i zaznacz, które mają być widoczne na ekranie startowym.",
        wraplength=700,
    ).pack(anchor="w")

    tree_frame = ttk.Frame(win, padding=(12, 4))
    tree_frame.pack(fill="both", expand=True)
    cols = ("visible", "name", "section", "folder")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18, selectmode="browse")
    tree.heading("visible", text="Pokaż")
    tree.heading("name", text="Komponent")
    tree.heading("section", text="Sekcja")
    tree.heading("folder", text="Folder")
    tree.column("visible", width=52, anchor="center")
    tree.column("name", width=220, anchor="w")
    tree.column("section", width=200, anchor="w")
    tree.column("folder", width=140, anchor="w")
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    row_state: dict[str, dict[str, object]] = {}

    def _sorted_components() -> list[Component]:
        def key(c: Component) -> tuple[str, str]:
            e = working.entries.get(c.folder_name)
            sec = e.section if e else ""
            return (sec.lower(), e.sort_key if e else c.order, c.name.lower())

        return sorted(all_components, key=key)

    def _refresh_tree() -> None:
        for iid in tree.get_children():
            tree.delete(iid)
        for comp in _sorted_components():
            e = working.entries.get(comp.folder_name)
            if e is None:
                e = TileLayoutEntry(
                    folder=comp.folder_name,
                    section=section_names[0],
                    visible=comp.folder_name in normally_visible,
                    sort_key=comp.order,
                )
                working.entries[comp.folder_name] = e
            vis_lbl = "tak" if e.visible else "—"
            tree.insert(
                "",
                "end",
                iid=comp.folder_name,
                values=(vis_lbl, comp.name, e.section, comp.folder_name),
            )
            row_state[comp.folder_name] = {"visible": e.visible, "section": e.section}

    _refresh_tree()

    edit = ttk.LabelFrame(win, text="Zaznaczony kafelek", padding=10)
    edit.pack(fill="x", padx=12, pady=4)

    visible_var = tk.BooleanVar(value=True)
    section_var = tk.StringVar(value=section_names[0])
    name_var = tk.StringVar(value="—")

    ttk.Checkbutton(edit, text="Pokaż na ekranie startowym", variable=visible_var).pack(anchor="w")
    sec_row = ttk.Frame(edit)
    sec_row.pack(fill="x", pady=(8, 0))
    ttk.Label(sec_row, text="Sekcja:").pack(side="left")
    section_combo = ttk.Combobox(
        sec_row,
        textvariable=section_var,
        values=section_names,
        width=36,
        state="readonly",
    )
    section_combo.pack(side="left", padx=(8, 0))
    ttk.Label(edit, textvariable=name_var, foreground="#555").pack(anchor="w", pady=(6, 0))

    current_folder: list[str] = []

    def _load_selection() -> None:
        sel = tree.selection()
        if not sel:
            current_folder.clear()
            name_var.set("— (zaznacz wiersz)")
            return
        folder = sel[0]
        current_folder[:] = [folder]
        comp = next((c for c in all_components if c.folder_name == folder), None)
        name_var.set(comp.name if comp else folder)
        st = row_state.get(folder, {})
        visible_var.set(bool(st.get("visible", True)))
        section_var.set(str(st.get("section") or section_names[0]))

    def _apply_row() -> None:
        if not current_folder:
            return
        folder = current_folder[0]
        vis = visible_var.get()
        sec = section_var.get().strip() or section_names[0]
        row_state[folder] = {"visible": vis, "section": sec}
        e = working.entries.get(folder)
        if e is None:
            e = TileLayoutEntry(folder=folder, section=sec, visible=vis, sort_key=0)
            working.entries[folder] = e
        e.visible = vis
        e.section = sec
        tree.set(folder, "visible", "tak" if vis else "—")
        tree.set(folder, "section", sec)

    def _on_select(_e: tk.Event | None = None) -> None:
        _load_selection()

    tree.bind("<<TreeviewSelect>>", _on_select)
    visible_var.trace_add("write", lambda *_a: _apply_row())
    section_combo.bind("<<ComboboxSelected>>", lambda _e: _apply_row())

    move = ttk.Frame(win, padding=(12, 0))
    move.pack(fill="x")
    ttk.Label(move, text="Kolejność w sekcji:").pack(side="left")

    def _move(delta: int) -> None:
        sel = tree.selection()
        if not sel:
            return
        folder = sel[0]
        comp = next((c for c in all_components if c.folder_name == folder), None)
        if comp is None:
            return
        e = working.entries.get(folder)
        if e is None:
            return
        same_sec = [
            c.folder_name
            for c in _sorted_components()
            if working.entries.get(c.folder_name, e).section == e.section
        ]
        try:
            idx = same_sec.index(folder)
        except ValueError:
            return
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(same_sec):
            return
        other = same_sec[new_idx]
        oe = working.entries.get(other)
        if oe is None:
            return
        e.sort_key, oe.sort_key = oe.sort_key, e.sort_key
        _refresh_tree()
        tree.selection_set(folder)
        tree.focus(folder)
        _load_selection()

    ttk.Button(move, text="▲ Wyżej", command=lambda: _move(-1)).pack(side="left", padx=(8, 4))
    ttk.Button(move, text="▼ Niżej", command=lambda: _move(1)).pack(side="left", padx=4)

    btns = ttk.Frame(win, padding=12)
    btns.pack(fill="x")

    def _reset() -> None:
        if not messagebox.askyesno(
            "Domyślny układ",
            "Przywrócić domyślne sekcje i widoczność kafelków?",
            parent=win,
        ):
            return
        nonlocal working
        working = build_default_layout(all_components, normally_visible=normally_visible)
        _refresh_tree()
        _load_selection()

    def _save() -> None:
        for folder, st in row_state.items():
            e = working.entries.get(folder)
            if e is None:
                continue
            e.visible = bool(st.get("visible", e.visible))
            e.section = str(st.get("section") or e.section)
        save_layout(working)
        on_saved(working)
        win.destroy()

    ttk.Button(btns, text="Zapisz", command=_save).pack(side="right", padx=(6, 0))
    ttk.Button(btns, text="Anuluj", command=win.destroy).pack(side="right")
    ttk.Button(btns, text="Domyślny układ", command=_reset).pack(side="left")

    if tree.get_children():
        tree.selection_set(tree.get_children()[0])
        _load_selection()
