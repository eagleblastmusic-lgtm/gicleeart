"""HF-3B GUI: bezpieczne zastosowanie szkicu do lokalnego wariantu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .home_flow_structure_gui import _text, _variant_combo, _variant_row
from .home_flow_structure_writer import (
    StructureWriterError,
    apply_structure_draft_to_variant,
    build_writer_plan,
    format_writer_plan,
    undo_last_structure_write,
    writer_undo_status,
)
from .homepage_variants import active_variant_id, variant_label


_BUTTON_TEXT = "Zastosuj szkic…"


def _open_writer(host: tk.Misc) -> None:
    current = getattr(host, "_giclee_home_structure_writer_window", None)
    if current is not None:
        try:
            if current.winfo_exists():
                current.lift()
                return
        except tk.TclError:
            pass

    variant_id = active_variant_id()
    win = tk.Toplevel(host)
    host._giclee_home_structure_writer_window = win  # type: ignore[attr-defined]
    win.title(f"HF-3B — Bounded Writer — {variant_label(variant_id)}")
    win.transient(host.winfo_toplevel())
    win.geometry("1040x720")
    win.minsize(860, 560)

    root = ttk.Frame(win, padding=(14, 12))
    root.pack(fill="both", expand=True)

    ttk.Label(
        root,
        text="GICLÉE HOME FLOW — HF-3B Bounded Writer",
        font=("", 14, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        root,
        text=(
            "Zapis tylko do index.json wybranego wariantu. "
            "Bez templates/index.json, bez assetów i bez deployu Shopify."
        ),
        foreground="#8a2f00",
        wraplength=980,
    ).pack(anchor="w", pady=(4, 10))

    body = ttk.Panedwindow(root, orient="horizontal")
    body.pack(fill="both", expand=True)
    preview_frame = ttk.LabelFrame(body, text="Podgląd operacji", padding=8)
    status_frame = ttk.LabelFrame(body, text="Undo i bariery", padding=8)
    body.add(preview_frame, weight=3)
    body.add(status_frame, weight=2)

    preview = tk.Text(preview_frame, wrap="word", padx=8, pady=8, state="disabled")
    preview_scroll = ttk.Scrollbar(
        preview_frame, orient="vertical", command=preview.yview
    )
    preview.configure(yscrollcommand=preview_scroll.set)
    preview.pack(side="left", fill="both", expand=True)
    preview_scroll.pack(side="right", fill="y")

    undo_text = tk.Text(status_frame, wrap="word", padx=8, pady=8, state="disabled")
    undo_text.pack(fill="both", expand=True)

    status_var = tk.StringVar(value="")
    ttk.Label(root, textvariable=status_var, foreground="#555").pack(
        anchor="w", pady=(8, 0)
    )

    buttons = ttk.Frame(root)
    buttons.pack(fill="x", pady=(10, 0))
    apply_button = ttk.Button(buttons, text="Zastosuj do wariantu")
    undo_button = ttk.Button(buttons, text="Cofnij ostatni zapis")
    refresh_button = ttk.Button(buttons, text="Odśwież")
    close_button = ttk.Button(buttons, text="Zamknij", command=win.destroy)
    apply_button.pack(side="right")
    undo_button.pack(side="right", padx=(0, 8))
    close_button.pack(side="left")
    refresh_button.pack(side="left", padx=(8, 0))

    current_plan: dict = {}

    def _set_text(widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def refresh() -> None:
        nonlocal current_plan
        current_plan = build_writer_plan(variant_id)
        _set_text(preview, format_writer_plan(current_plan))

        undo = writer_undo_status(variant_id)
        undo_lines = [
            "UNDO OSTATNIEJ OPERACJI",
            "",
            str(undo.get("reason") or ""),
            "",
            "Warunki Undo:",
            "  • bieżący index.json musi mieć hash zapisany po HF-3B,",
            "  • backup musi istnieć i zgadzać się z hashem sprzed operacji,",
            "  • po ręcznej zmianie pliku Undo jest blokowane.",
        ]
        if undo.get("backup_path"):
            undo_lines.extend(["", f"Backup: {undo['backup_path']}"])
        _set_text(undo_text, "\n".join(undo_lines))

        apply_button.configure(
            state="normal" if current_plan.get("ready") else "disabled"
        )
        undo_button.configure(state="normal" if undo.get("available") else "disabled")
        if current_plan.get("ready"):
            status_var.set(
                "Plan przeszedł walidację. Zapis wymaga wpisania frazy potwierdzającej."
            )
        else:
            status_var.set("Operacja jest zablokowana albo szkic nie zmienia kolejności.")

    def apply() -> None:
        phrase = f"ZASTOSUJ {variant_id}"
        answer = simpledialog.askstring(
            "HF-3B — potwierdzenie",
            (
                "Writer utworzy dokładny backup i zmieni index.json wyłącznie "
                f"wariantu «{variant_label(variant_id)}».\n\n"
                f"Wpisz dokładnie: {phrase}"
            ),
            parent=win,
        )
        if answer != phrase:
            if answer is not None:
                status_var.set("Nieprawidłowa fraza — zapis anulowany.")
            return
        try:
            result = apply_structure_draft_to_variant(
                variant_id,
                expected_source_sha256=str(current_plan.get("source_sha256") or ""),
            )
        except StructureWriterError as exc:
            messagebox.showerror("HF-3B", str(exc), parent=win)
            refresh()
            return
        messagebox.showinfo(
            "HF-3B",
            (
                "Zastosowano kolejność do lokalnego wariantu.\n\n"
                f"Backup:\n{result['backup_path']}\n\n"
                "templates/index.json i Shopify nie zostały zmienione."
            ),
            parent=win,
        )
        refresh()

    def undo() -> None:
        phrase = f"COFNIJ {variant_id}"
        answer = simpledialog.askstring(
            "HF-3B — Undo",
            (
                "Zostanie przywrócony dokładny backup sprzed ostatniej operacji.\n\n"
                f"Wpisz dokładnie: {phrase}"
            ),
            parent=win,
        )
        if answer != phrase:
            if answer is not None:
                status_var.set("Nieprawidłowa fraza — Undo anulowane.")
            return
        try:
            result = undo_last_structure_write(variant_id)
        except StructureWriterError as exc:
            messagebox.showerror("HF-3B — Undo", str(exc), parent=win)
            refresh()
            return
        messagebox.showinfo(
            "HF-3B — Undo",
            f"Przywrócono dokładny plik:\n{result['restored_from']}",
            parent=win,
        )
        refresh()

    apply_button.configure(command=apply)
    undo_button.configure(command=undo)
    refresh_button.configure(command=refresh)
    refresh()

    def on_destroy(event=None) -> None:
        if event is not None and getattr(event, "widget", None) is not win:
            return
        if getattr(host, "_giclee_home_structure_writer_window", None) is win:
            host._giclee_home_structure_writer_window = None  # type: ignore[attr-defined]

    win.bind("<Destroy>", on_destroy)


def _decorate(host: tk.Misc) -> None:
    if getattr(host, "_giclee_home_structure_writer_decorated", False):
        return
    row = _variant_row(host)
    if row is None:
        return

    host._giclee_home_structure_writer_decorated = True  # type: ignore[attr-defined]
    hint = next(
        (
            child
            for child in row.winfo_children()
            if isinstance(child, ttk.Label) and "Każda wersja" in _text(child)
        ),
        None,
    )
    button = ttk.Button(row, text=_BUTTON_TEXT, command=lambda: _open_writer(host))
    try:
        button.pack(side="left", padx=(4, 0), before=hint)
    except tk.TclError:
        button.pack(side="left", padx=(4, 0))

    combo = _variant_combo(row)
    if combo is not None:

        def close_stale(_event=None) -> None:
            window = getattr(host, "_giclee_home_structure_writer_window", None)
            if window is not None:
                try:
                    if window.winfo_exists():
                        window.destroy()
                except tk.TclError:
                    pass

        combo.bind("<<ComboboxSelected>>", close_stale, add="+")


def install_home_flow_structure_writer_gui() -> None:
    from . import gui

    current = gui._build_ui
    if getattr(current, "_giclee_home_structure_writer_wrapped", False):
        return

    def build_ui(host: tk.Misc, *, inline: bool = False) -> None:
        current(host, inline=inline)
        host.after_idle(lambda: _decorate(host))

    setattr(build_ui, "_giclee_home_structure_writer_wrapped", True)
    setattr(build_ui, "__wrapped__", current)
    gui._build_ui = build_ui
