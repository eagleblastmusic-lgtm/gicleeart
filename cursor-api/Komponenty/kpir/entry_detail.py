"""Okno szczegółów wpisu KPiR z historią zmian."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .constants import ENTRY_SOURCE_LABELS, ENTRY_STATUS_LABELS, KPIR_COLUMN_LABELS
from .models import KpirEntry
from .storage import get_entry, list_changelog_for_entry


def open_entry_detail(
    parent: tk.Misc,
    entry_id: str,
    *,
    on_open_linked: Callable[[str], None] | None = None,
) -> None:
    entry = get_entry(entry_id)
    if not entry:
        messagebox.showerror("KPiR", "Nie znaleziono wpisu.", parent=parent)
        return

    win = tk.Toplevel(parent)
    win.title(f"Wpis KPiR — {entry.entry_number}")
    position_toplevel_screen_center(win, 720, 620)
    win.transient(parent.winfo_toplevel())

    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    tab_detail = ttk.Frame(notebook, padding=8)
    tab_history = ttk.Frame(notebook, padding=8)
    notebook.add(tab_detail, text="Szczegóły")
    notebook.add(tab_history, text="Historia zmian")

    _build_detail_tab(tab_detail, entry, on_open_linked=on_open_linked)
    _build_history_tab(tab_history, entry)

    ttk.Button(win, text="Zamknij", command=win.destroy).pack(pady=(0, 10))


def _build_detail_tab(
    parent: ttk.Frame,
    entry: KpirEntry,
    *,
    on_open_linked: Callable[[str], None] | None,
) -> None:
    canvas = tk.Canvas(parent, highlightthickness=0)
    vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def _on_configure(_e: tk.Event | None = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(win_id, width=canvas.winfo_width())

    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_configure)
    bind_mousewheel_to_canvas(canvas, inner)

    rows: list[tuple[str, str]] = [
        ("Numer wpisu", entry.entry_number),
        ("ID", entry.id),
        ("Status", ENTRY_STATUS_LABELS.get(entry.status, entry.status)),
        ("Źródło", ENTRY_SOURCE_LABELS.get(entry.source, entry.source)),
        ("Typ", entry.entry_type),
        ("Data zdarzenia", entry.event_date),
        ("Numer dowodu", entry.document_number),
        ("Kontrahent", entry.contractor),
        ("Adres kontrahenta", entry.contractor_address or "—"),
        ("Opis", entry.description),
        ("", ""),
        (KPIR_COLUMN_LABELS["revenue_goods"], f"{entry.revenue_goods:.2f} PLN"),
        (KPIR_COLUMN_LABELS["revenue_other"], f"{entry.revenue_other:.2f} PLN"),
        ("Razem przychód", f"{entry.total_revenue:.2f} PLN"),
        (KPIR_COLUMN_LABELS["purchase_goods"], f"{entry.purchase_goods:.2f} PLN"),
        (KPIR_COLUMN_LABELS["purchase_side"], f"{entry.purchase_side:.2f} PLN"),
        (KPIR_COLUMN_LABELS["wages"], f"{entry.wages:.2f} PLN"),
        (KPIR_COLUMN_LABELS["other_expenses"], f"{entry.other_expenses:.2f} PLN"),
        ("Razem koszty", f"{entry.total_costs:.2f} PLN"),
        ("", ""),
        ("Waluta oryginalna", entry.original_currency),
        ("Kwota oryginalna", f"{entry.original_amount:.2f}"),
        ("Kurs NBP", f"{entry.nbp_rate:.4f}" if entry.nbp_rate else "—"),
        ("Data kursu NBP", entry.nbp_rate_date or "—"),
        ("Tabela NBP", entry.nbp_table_number or "—"),
        ("Status kursu", entry.nbp_status),
        ("Kwota PLN", f"{entry.amount_pln:.2f} PLN"),
        ("Kraj", entry.country or "—"),
        ("Kategoria", entry.category or "—"),
        ("", ""),
        ("Zamówienie Shopify", entry.shopify_order_name or "—"),
        ("ID zamówienia", str(entry.shopify_order_id) if entry.shopify_order_id else "—"),
        ("ID faktury", entry.invoice_id or "—"),
        ("ID kosztu", entry.cost_id or "—"),
        ("Utworzono", entry.created_at or "—"),
        ("Zmodyfikowano", entry.updated_at or "—"),
        ("Uwagi", entry.notes or "—"),
    ]

    if entry.entry_type == "correction":
        rows.extend([
            ("", ""),
            ("— Korekta —", ""),
            ("Powiązany wpis", entry.linked_entry_id or "—"),
            ("Przyczyna", entry.correction_reason or "—"),
            ("Kwota przed", f"{entry.amount_before_correction:.2f} PLN"),
            ("Kwota korekty", f"{entry.correction_amount:.2f} PLN"),
            ("Kwota po", f"{entry.amount_after_correction:.2f} PLN"),
        ])

    for i, (lbl, val) in enumerate(rows):
        if not lbl and not val:
            ttk.Separator(inner, orient="horizontal").grid(
                row=i, column=0, columnspan=2, sticky="ew", pady=6,
            )
            continue
        font = ("Segoe UI", 9, "bold") if lbl.startswith("Razem") or lbl.startswith("—") else ("Segoe UI", 9)
        ttk.Label(inner, text=lbl + ":", font=font).grid(row=i, column=0, sticky="nw", padx=(0, 8), pady=2)
        ttk.Label(inner, text=val, wraplength=480, justify="left").grid(row=i, column=1, sticky="w", pady=2)

    inner.columnconfigure(1, weight=1)

    if entry.linked_entry_id:
        btn_row = ttk.Frame(inner)
        btn_row.grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=(10, 0))

        def _open_linked() -> None:
            if on_open_linked:
                on_open_linked(entry.linked_entry_id)
            else:
                open_entry_detail(parent.winfo_toplevel(), entry.linked_entry_id)

        ttk.Button(
            btn_row,
            text=f"Pokaż powiązany wpis ({entry.linked_entry_id})",
            command=_open_linked,
        ).pack(side="left")


def _build_history_tab(parent: ttk.Frame, entry: KpirEntry) -> None:
    logs = list_changelog_for_entry(entry.id)
    if not logs:
        ttk.Label(
            parent,
            text="Brak zapisanych zmian dla tego wpisu.\n"
                 "Historia jest tworzona przy edycji zaksięgowanych wpisów.",
            foreground="#666",
        ).pack(anchor="w", pady=8)
        return

    tree_frame = ttk.Frame(parent)
    tree_frame.pack(fill="both", expand=True)
    cols = ("when", "field", "old", "new", "reason")
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
    for cid, txt, w in [
        ("when", "Kiedy", 130), ("field", "Pole", 100),
        ("old", "Poprzednio", 120), ("new", "Nowa wartość", 120), ("reason", "Powód", 140),
    ]:
        tree.heading(cid, text=txt)
        tree.column(cid, width=w)
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    for log in sorted(logs, key=lambda x: x.changed_at, reverse=True):
        tree.insert("", "end", values=(
            log.changed_at[:19],
            log.field_name,
            log.old_value[:40],
            log.new_value[:40],
            log.reason or "—",
        ))

    ttk.Label(
        parent,
        text=f"Łącznie {len(logs)} zmian",
        foreground="#666",
    ).pack(anchor="w", pady=(6, 0))
