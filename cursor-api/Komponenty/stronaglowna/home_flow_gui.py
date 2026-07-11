"""Nakładka GUI dla osi GICLÉE HOME FLOW.

Istniejący edytor sekcji pozostaje źródłem logiki zapisu. Ukryty Listbox nadal
steruje prawym panelem, a Treeview pokazuje sekcje i przypisane do nich fazy.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Iterable

from .home_flow import (
    HomeFlowItem,
    owner_zone_id,
    reset_flow_name,
    resolve_flow_items,
    set_flow_name,
)
from .homepage_variants import active_variant_id, variant_label
from .registry import HOME_ZONES

_FLOW_BUTTON_TEXT = "GICLÉE HOME FLOW…"
_FLOW_APP_TITLE = "GICLÉE HOME FLOW — strona główna"


def _walk(widget: tk.Misc) -> Iterable[tk.Misc]:
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def _widget_text(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("text") or "")
    except (tk.TclError, AttributeError):
        return ""


def _find_section_list(host: tk.Misc) -> tk.Listbox | None:
    for widget in _walk(host):
        if not isinstance(widget, tk.Listbox):
            continue
        parent = widget.master
        if isinstance(parent, ttk.LabelFrame) and _widget_text(parent) == "Sekcje strony głównej":
            return widget
    return None


def _find_variant_row(host: tk.Misc) -> ttk.Frame | None:
    for widget in _walk(host):
        if isinstance(widget, ttk.Button) and _widget_text(widget) == "Zmień nazwę…":
            parent = widget.master
            return parent if isinstance(parent, ttk.Frame) else None
    return None


def _find_variant_combo(row: ttk.Frame | None) -> ttk.Combobox | None:
    if row is None:
        return None
    return next((child for child in row.winfo_children() if isinstance(child, ttk.Combobox)), None)


def _zone_index(zone_id: str) -> int | None:
    for index, zone in enumerate(HOME_ZONES):
        if zone.zone_id == zone_id:
            return index
    return None


def _selected_list_index(listbox: tk.Listbox) -> int | None:
    selection = listbox.curselection()
    return int(selection[0]) if selection else None


def _insert_flow_rows(tree: ttk.Treeview, items: tuple[HomeFlowItem, ...]) -> None:
    roots = tree.get_children("")
    if roots:
        tree.delete(*roots)

    known_ids = {item.stable_id for item in items}
    for item in items:
        parent = item.parent_id if item.kind == "phase" and item.parent_id in known_ids else ""
        prefix = "●" if item.kind == "section" else "↳"
        tree.insert(
            parent,
            "end",
            iid=item.stable_id,
            text=f"{prefix} {item.code}  {item.display_name}",
            values=(
                "Sekcja" if item.kind == "section" else "Faza",
                item.stable_id,
                item.placement if item.kind == "phase" else "—",
            ),
            tags=(item.kind,),
            open=True,
        )


def _open_flow_editor(host: tk.Misc, refresh_navigation: Callable[[], None]) -> None:
    existing = getattr(host, "_giclee_home_flow_window", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.lift()
                existing.focus_force()
                return
        except tk.TclError:
            pass

    win = tk.Toplevel(host)
    host._giclee_home_flow_window = win  # type: ignore[attr-defined]
    win.title(f"GICLÉE HOME FLOW — {variant_label(active_variant_id())}")
    win.transient(host.winfo_toplevel())
    win.geometry("940x690")
    win.minsize(760, 520)

    pad = ttk.Frame(win, padding=(16, 14))
    pad.pack(fill="both", expand=True)

    ttk.Label(pad, text="GICLÉE HOME FLOW", font=("", 14, "bold")).pack(anchor="w")
    ttk.Label(
        pad,
        text=(
            "Oś przebiegu strony głównej. Kody GH-xx i GH-Txx są wyliczane automatycznie "
            "z aktualnej kolejności; techniczne identyfikatory pozostają stabilne."
        ),
        foreground="#555",
        wraplength=880,
    ).pack(anchor="w", pady=(4, 12))

    tree = ttk.Treeview(
        pad,
        columns=("kind", "technical", "placement"),
        show="tree headings",
        selectmode="browse",
    )
    tree.heading("#0", text="Kod i nazwa")
    tree.heading("kind", text="Typ")
    tree.heading("technical", text="ID techniczne")
    tree.heading("placement", text="Położenie")
    tree.column("#0", width=490, minwidth=280, stretch=True)
    tree.column("kind", width=90, anchor="center", stretch=False)
    tree.column("technical", width=220, stretch=False)
    tree.column("placement", width=100, anchor="center", stretch=False)
    tree.tag_configure("section", font=("", 10, "bold"))
    tree.tag_configure("phase", foreground="#666")
    tree.pack(fill="both", expand=True)

    status_var = tk.StringVar(
        value="Zmiana nazw zapisuje wyłącznie metadane wariantu — nie modyfikuje index.json ani motywu Shopify."
    )
    ttk.Label(pad, textvariable=status_var, foreground="#666", wraplength=880).pack(
        anchor="w", pady=(10, 0)
    )

    def refresh_window(*, keep_selection: str = "") -> None:
        items = resolve_flow_items(active_variant_id())
        _insert_flow_rows(tree, items)
        win.title(f"GICLÉE HOME FLOW — {variant_label(active_variant_id())}")
        target = keep_selection if keep_selection and tree.exists(keep_selection) else ""
        if not target:
            roots = tree.get_children("")
            target = roots[0] if roots else ""
        if target:
            tree.selection_set(target)
            tree.focus(target)
            tree.see(target)

    def selected_id() -> str:
        selection = tree.selection()
        return str(selection[0]) if selection else ""

    def rename_selected(_event=None) -> None:
        stable_id = selected_id()
        if not stable_id:
            return
        item = next(
            (row for row in resolve_flow_items(active_variant_id()) if row.stable_id == stable_id),
            None,
        )
        if item is None:
            return
        new_name = simpledialog.askstring(
            "GICLÉE HOME FLOW",
            f"Nowa nazwa dla {item.code}:\n\nID techniczne: {item.stable_id}",
            initialvalue=item.display_name,
            parent=win,
        )
        if new_name is None:
            return
        try:
            set_flow_name(active_variant_id(), stable_id, new_name)
        except ValueError as exc:
            messagebox.showerror("GICLÉE HOME FLOW", str(exc), parent=win)
            return
        refresh_window(keep_selection=stable_id)
        refresh_navigation()
        status_var.set(
            f"Zapisano nazwę «{new_name.strip()}» dla wariantu {variant_label(active_variant_id())}."
        )

    def restore_selected() -> None:
        stable_id = selected_id()
        if not stable_id:
            return
        reset_flow_name(active_variant_id(), stable_id)
        refresh_window(keep_selection=stable_id)
        refresh_navigation()
        status_var.set("Przywrócono nazwę domyślną.")

    controls = ttk.Frame(pad)
    controls.pack(fill="x", pady=(12, 0))
    ttk.Button(controls, text="Zmień nazwę…", command=rename_selected).pack(side="left")
    ttk.Button(controls, text="Przywróć domyślną", command=restore_selected).pack(
        side="left", padx=(8, 0)
    )
    ttk.Button(controls, text="Zamknij", command=win.destroy).pack(side="right")

    tree.bind("<Double-1>", rename_selected)
    refresh_window()

    def on_destroy(event=None) -> None:
        if event is not None and getattr(event, "widget", None) is not win:
            return
        if getattr(host, "_giclee_home_flow_window", None) is win:
            host._giclee_home_flow_window = None  # type: ignore[attr-defined]

    win.bind("<Destroy>", on_destroy)


def _decorate_home_editor(host: tk.Misc) -> None:
    if getattr(host, "_giclee_home_flow_decorated", False):
        return

    listbox = _find_section_list(host)
    variant_row = _find_variant_row(host)
    if listbox is None or variant_row is None:
        return

    host._giclee_home_flow_decorated = True  # type: ignore[attr-defined]
    section_frame = listbox.master
    guard = {"list_event": False}

    tree = ttk.Treeview(section_frame, show="tree", selectmode="browse")
    tree.column("#0", width=330, minwidth=220, stretch=True)
    tree.tag_configure("section", font=("", 9, "bold"))
    tree.tag_configure("phase", foreground="#666")

    siblings = section_frame.winfo_children()
    status_widget = next((row for row in siblings if row is not listbox), None)
    listbox.pack_forget()
    try:
        tree.pack(fill="both", expand=True, before=status_widget)
    except tk.TclError:
        tree.pack(fill="both", expand=True)

    def current_items() -> tuple[HomeFlowItem, ...]:
        return resolve_flow_items(active_variant_id())

    def select_tree_for_zone(zone_id: str) -> None:
        items = current_items()
        section = next(
            (item for item in items if item.kind == "section" and item.zone_id == zone_id),
            None,
        )
        if section is None or not tree.exists(section.stable_id):
            return
        tree.selection_set(section.stable_id)
        tree.focus(section.stable_id)
        tree.see(section.stable_id)

    def refresh_navigation() -> None:
        items = current_items()
        previous = tree.selection()[0] if tree.selection() else ""
        _insert_flow_rows(tree, items)
        if previous and tree.exists(previous):
            tree.selection_set(previous)
            tree.focus(previous)
            tree.see(previous)
            return
        index = _selected_list_index(listbox)
        if index is not None and 0 <= index < len(HOME_ZONES):
            select_tree_for_zone(HOME_ZONES[index].zone_id)

    def on_tree_select(_event=None) -> None:
        selection = tree.selection()
        if not selection:
            return
        items = current_items()
        item = next((row for row in items if row.stable_id == selection[0]), None)
        if item is None:
            return
        zone_id = owner_zone_id(item, items)
        index = _zone_index(zone_id)
        if index is None:
            return
        guard["list_event"] = True
        try:
            listbox.selection_clear(0, "end")
            listbox.selection_set(index)
            listbox.activate(index)
            listbox.event_generate("<<ListboxSelect>>")
        finally:
            guard["list_event"] = False

    def on_hidden_list_select(_event=None) -> None:
        if guard["list_event"]:
            return
        index = _selected_list_index(listbox)
        if index is not None and 0 <= index < len(HOME_ZONES):
            select_tree_for_zone(HOME_ZONES[index].zone_id)

    tree.bind("<<TreeviewSelect>>", on_tree_select)
    listbox.bind("<<ListboxSelect>>", on_hidden_list_select, add="+")

    flow_button = ttk.Button(
        variant_row,
        text=_FLOW_BUTTON_TEXT,
        command=lambda: _open_flow_editor(host, refresh_navigation),
    )
    hint_widget = next(
        (
            child
            for child in variant_row.winfo_children()
            if isinstance(child, ttk.Label) and "Każda wersja" in _widget_text(child)
        ),
        None,
    )
    try:
        flow_button.pack(side="left", padx=(8, 0), before=hint_widget)
    except tk.TclError:
        flow_button.pack(side="left", padx=(8, 0))

    combo = _find_variant_combo(variant_row)
    if combo is not None:
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event=None: host.after(120, refresh_navigation),
            add="+",
        )

    refresh_navigation()


def install_home_flow_gui() -> None:
    from . import gui

    gui.APP_TITLE = _FLOW_APP_TITLE
    current = gui._build_ui
    if getattr(current, "_giclee_home_flow_wrapped", False):
        return

    def build_ui_with_home_flow(host: tk.Misc, *, inline: bool = False) -> None:
        current(host, inline=inline)
        host.after_idle(lambda: _decorate_home_editor(host))

    setattr(build_ui_with_home_flow, "_giclee_home_flow_wrapped", True)
    setattr(build_ui_with_home_flow, "__wrapped__", current)
    gui._build_ui = build_ui_with_home_flow
