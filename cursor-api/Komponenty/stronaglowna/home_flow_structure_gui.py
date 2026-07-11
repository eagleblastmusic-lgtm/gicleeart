"""HF-3A GUI: planner struktury bez writer-a motywu."""

from __future__ import annotations

import copy
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Iterable

from .home_flow import HomeFlowItem
from .home_flow_structure import (
    CORE_SECTION_IDS,
    LOCKED_PREFIX,
    LOCKED_SUFFIX,
    SECTION_BLUEPRINTS,
    add_custom_section,
    build_structure_plan,
    format_structure_plan,
    is_custom_section,
    load_structure_draft,
    move_section,
    remove_custom_section,
    reorder_section,
    reset_structure_draft,
    resolve_structure_items,
    save_structure_draft,
)
from .homepage_variants import active_variant_id, variant_label

_BUTTON_TEXT = "Plan struktury…"


def _walk(widget: tk.Misc) -> Iterable[tk.Misc]:
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def _text(widget: tk.Misc) -> str:
    try:
        return str(widget.cget("text") or "")
    except (tk.TclError, AttributeError):
        return ""


def _variant_row(host: tk.Misc) -> ttk.Frame | None:
    for widget in _walk(host):
        if isinstance(widget, ttk.Button) and _text(widget) == "Zmień nazwę…":
            return widget.master if isinstance(widget.master, ttk.Frame) else None
    return None


def _variant_combo(row: ttk.Frame | None) -> ttk.Combobox | None:
    if row is None:
        return None
    return next((child for child in row.winfo_children() if isinstance(child, ttk.Combobox)), None)


def _fill_tree(tree: ttk.Treeview, items: tuple[HomeFlowItem, ...]) -> None:
    roots = tree.get_children("")
    if roots:
        tree.delete(*roots)
    known = {item.stable_id for item in items}
    locked = set(LOCKED_PREFIX) | set(LOCKED_SUFFIX)
    for item in items:
        parent = item.parent_id if item.kind == "phase" and item.parent_id in known else ""
        if item.kind == "phase":
            prefix, status, tag = "↳", "Faza", "phase"
        elif item.stable_id in locked:
            prefix, status, tag = "◆", "Kotwica", "locked"
        elif is_custom_section(item.stable_id):
            prefix, status, tag = "＋", "Nowa", "custom"
        else:
            prefix, status, tag = "●", "Sekcja", "section"
        tree.insert(
            parent,
            "end",
            iid=item.stable_id,
            text=f"{prefix} {item.code}  {item.display_name}",
            values=(status, item.stable_id),
            tags=(tag,),
            open=True,
        )


def _open_planner(host: tk.Misc) -> None:
    current = getattr(host, "_giclee_home_structure_window", None)
    if current is not None:
        try:
            if current.winfo_exists():
                current.lift()
                return
        except tk.TclError:
            pass

    variant_id = active_variant_id()
    working = copy.deepcopy(load_structure_draft(variant_id))
    saved = copy.deepcopy(working)
    drag_source = {"id": ""}

    win = tk.Toplevel(host)
    host._giclee_home_structure_window = win  # type: ignore[attr-defined]
    win.title(f"HF-3A — Plan struktury — {variant_label(variant_id)}")
    win.transient(host.winfo_toplevel())
    win.geometry("1180x740")
    win.minsize(940, 600)

    root = ttk.Frame(win, padding=(14, 12))
    root.pack(fill="both", expand=True)
    ttk.Label(root, text="GICLÉE HOME FLOW — HF-3A Structure Planner", font=("", 14, "bold")).pack(anchor="w")
    ttk.Label(
        root,
        text="SZKIC: nie zmienia index.json, assetów motywu ani Shopify. Fazy przesuwają się razem z sekcją.",
        foreground="#8a5a00",
        wraplength=1120,
    ).pack(anchor="w", pady=(4, 10))

    body = ttk.Panedwindow(root, orient="horizontal")
    body.pack(fill="both", expand=True)
    left = ttk.LabelFrame(body, text="Szkic osi", padding=8)
    right = ttk.LabelFrame(body, text="Dry-run / readiness", padding=8)
    body.add(left, weight=3)
    body.add(right, weight=2)

    tree = ttk.Treeview(left, columns=("kind", "technical"), show="tree headings", selectmode="browse")
    tree.heading("#0", text="Kod i nazwa")
    tree.heading("kind", text="Status")
    tree.heading("technical", text="ID techniczne")
    tree.column("#0", width=450, minwidth=260, stretch=True)
    tree.column("kind", width=90, anchor="center", stretch=False)
    tree.column("technical", width=220, stretch=False)
    tree.tag_configure("locked", font=("", 10, "bold"))
    tree.tag_configure("section", font=("", 10, "bold"))
    tree.tag_configure("custom", font=("", 10, "bold"), foreground="#7a4b00")
    tree.tag_configure("phase", foreground="#666")
    tree.pack(fill="both", expand=True)

    plan = tk.Text(right, wrap="word", padx=8, pady=8, state="disabled")
    scroll = ttk.Scrollbar(right, orient="vertical", command=plan.yview)
    plan.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    plan.pack(side="left", fill="both", expand=True)

    status = tk.StringVar(value="Szkic wczytany do RAM.")
    ttk.Label(root, textvariable=status, foreground="#666", wraplength=1120).pack(anchor="w", pady=(8, 0))

    blueprint_labels = {row.label: row.blueprint_id for row in SECTION_BLUEPRINTS}
    blueprint_var = tk.StringVar(value=SECTION_BLUEPRINTS[0].label)

    def selected_id() -> str:
        selection = tree.selection()
        return str(selection[0]) if selection else ""

    def refresh(keep: str = "") -> None:
        _fill_tree(tree, resolve_structure_items(variant_id, draft=working))
        target = keep if keep and tree.exists(keep) else ""
        if not target:
            roots = tree.get_children("")
            target = roots[0] if roots else ""
        if target:
            tree.selection_set(target)
            tree.focus(target)
            tree.see(target)
        text = format_structure_plan(build_structure_plan(variant_id, working))
        plan.configure(state="normal")
        plan.delete("1.0", "end")
        plan.insert("1.0", text)
        plan.configure(state="disabled")

    def replace(next_draft: dict, keep: str = "", message: str = "") -> None:
        nonlocal working
        working = next_draft
        refresh(keep)
        if message:
            status.set(message)

    def move(direction: int) -> None:
        stable_id = selected_id()
        if not stable_id:
            return
        if stable_id.startswith("phase:"):
            status.set("Faza jest przypisana do sekcji i nie jest przesuwana osobno.")
            return
        try:
            replace(move_section(working, stable_id, direction), stable_id, "Zmieniono kolejność w RAM.")
        except ValueError as exc:
            status.set(str(exc))

    def add_section() -> None:
        blueprint_id = blueprint_labels.get(blueprint_var.get())
        if not blueprint_id:
            return
        name = simpledialog.askstring("Nowa sekcja", "Nazwa użytkowa sekcji:", initialvalue=blueprint_var.get(), parent=win)
        if name is None:
            return
        try:
            next_draft, stable_id = add_custom_section(working, blueprint_id, name)
            replace(next_draft, stable_id, "Dodano blueprint do szkicu; Shopify pozostaje nietknięty.")
        except ValueError as exc:
            messagebox.showerror("HF-3A", str(exc), parent=win)

    def remove_section() -> None:
        stable_id = selected_id()
        try:
            replace(remove_custom_section(working, stable_id), message="Usunięto nową sekcję ze szkicu.")
        except ValueError as exc:
            status.set(str(exc))

    def restore_saved() -> None:
        nonlocal working
        working = copy.deepcopy(saved)
        refresh()
        status.set("Przywrócono ostatni zapisany szkic do RAM.")

    def restore_canonical() -> None:
        nonlocal working
        if not messagebox.askyesno("Przywróć oś", "Przywrócić kanoniczną kolejność w RAM?", parent=win):
            return
        working = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
        refresh()
        status.set("Przywrócono kanoniczną oś w RAM.")

    def save() -> None:
        nonlocal saved
        try:
            save_structure_draft(variant_id, working)
        except ValueError as exc:
            messagebox.showerror("HF-3A — blokery", str(exc), parent=win)
            return
        saved = copy.deepcopy(working)
        refresh(selected_id())
        status.set("Zapisano structure_draft w home_flow.json; index.json nie został zmieniony.")

    def clear_saved() -> None:
        nonlocal working, saved
        if not messagebox.askyesno("Usuń szkic", "Usunąć zapisany structure_draft? Nazwy pozostaną.", parent=win):
            return
        reset_structure_draft(variant_id)
        working = load_structure_draft(variant_id)
        saved = copy.deepcopy(working)
        refresh()
        status.set("Usunięto zapisany szkic.")

    controls = ttk.Frame(root)
    controls.pack(fill="x", pady=(10, 0))
    ttk.Button(controls, text="▲ Wyżej", command=lambda: move(-1)).pack(side="left")
    ttk.Button(controls, text="▼ Niżej", command=lambda: move(1)).pack(side="left", padx=(6, 0))
    ttk.Combobox(
        controls,
        textvariable=blueprint_var,
        values=list(blueprint_labels),
        state="readonly",
        width=28,
    ).pack(side="left", padx=(14, 4))
    ttk.Button(controls, text="Dodaj sekcję", command=add_section).pack(side="left")
    ttk.Button(controls, text="Usuń nową", command=remove_section).pack(side="left", padx=(6, 0))
    ttk.Button(controls, text="Oś kanoniczna", command=restore_canonical).pack(side="left", padx=(12, 0))
    ttk.Button(controls, text="Przywróć zapisany", command=restore_saved).pack(side="left", padx=(6, 0))
    ttk.Button(controls, text="Usuń szkic…", command=clear_saved).pack(side="left", padx=(6, 0))
    ttk.Button(controls, text="Zamknij", command=win.destroy).pack(side="right")
    ttk.Button(controls, text="Zapisz szkic", command=save).pack(side="right", padx=(0, 8))

    def drag_press(event) -> None:
        iid = tree.identify_row(event.y)
        drag_source["id"] = iid if iid and not iid.startswith("phase:") else ""

    def drag_motion(event) -> None:
        iid = tree.identify_row(event.y)
        if iid:
            tree.selection_set(iid)

    def drag_release(event) -> None:
        source_id = drag_source.get("id") or ""
        drag_source["id"] = ""
        target_id = tree.identify_row(event.y)
        if not source_id or not target_id or target_id.startswith("phase:"):
            return
        try:
            replace(reorder_section(working, source_id, target_id), source_id, "Przestawiono sekcję drag-and-drop w RAM.")
        except ValueError as exc:
            status.set(str(exc))
            refresh(source_id)

    tree.bind("<ButtonPress-1>", drag_press, add="+")
    tree.bind("<B1-Motion>", drag_motion, add="+")
    tree.bind("<ButtonRelease-1>", drag_release, add="+")
    win.bind("<Alt-Up>", lambda _event=None: move(-1))
    win.bind("<Alt-Down>", lambda _event=None: move(1))
    refresh()

    def on_destroy(event=None) -> None:
        if event is not None and getattr(event, "widget", None) is not win:
            return
        if getattr(host, "_giclee_home_structure_window", None) is win:
            host._giclee_home_structure_window = None  # type: ignore[attr-defined]

    win.bind("<Destroy>", on_destroy)


def _decorate(host: tk.Misc) -> None:
    if getattr(host, "_giclee_home_structure_decorated", False):
        return
    row = _variant_row(host)
    if row is None:
        return
    host._giclee_home_structure_decorated = True  # type: ignore[attr-defined]
    hint = next((child for child in row.winfo_children() if isinstance(child, ttk.Label) and "Każda wersja" in _text(child)), None)
    button = ttk.Button(row, text=_BUTTON_TEXT, command=lambda: _open_planner(host))
    try:
        button.pack(side="left", padx=(4, 0), before=hint)
    except tk.TclError:
        button.pack(side="left", padx=(4, 0))

    combo = _variant_combo(row)
    if combo is not None:
        def close_stale(_event=None) -> None:
            window = getattr(host, "_giclee_home_structure_window", None)
            if window is not None:
                try:
                    if window.winfo_exists():
                        window.destroy()
                except tk.TclError:
                    pass
        combo.bind("<<ComboboxSelected>>", close_stale, add="+")


def install_home_flow_structure_gui() -> None:
    from . import gui

    current = gui._build_ui
    if getattr(current, "_giclee_home_structure_wrapped", False):
        return

    def build_ui(host: tk.Misc, *, inline: bool = False) -> None:
        current(host, inline=inline)
        host.after_idle(lambda: _decorate(host))

    setattr(build_ui, "_giclee_home_structure_wrapped", True)
    setattr(build_ui, "__wrapped__", current)
    gui._build_ui = build_ui
