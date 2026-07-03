"""GUI: Wzorzec szablonu — lista produktów + przypisanie template_suffix (szablon motywu)."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from typing import Any

from Komponenty._shared.storefront_urls import product_storefront_url
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .service import (
    apply_template_suffix_batch,
    load_catalog_with_template_suffix,
    sort_catalog_rows,
    template_display_label,
)

APP_TITLE = "Wzorzec szablonu — szablon motywu produktu"


def main() -> None:
    root = tk.Tk()
    root.title(APP_TITLE)
    position_toplevel_screen_center(root, 1280, 820)
    root.minsize(980, 620)
    _build_ui(root)
    root.mainloop()


def _build_ui(host: tk.Misc, *, inline: bool = False) -> None:
    state: dict[str, Any] = {
        "rows": [],
        "templates": [],
        "suffix_by_label": {},
        "label_by_suffix": {},
        "sort_col": "artist",
        "sort_reverse": False,
        "busy": False,
    }

    top = ttk.LabelFrame(
        host,
        text="Produkty (Ctrl+klik / Shift+klik — wiele zaznaczeń)",
        padding=(10, 8),
    )
    top.pack(fill="both", expand=True, padx=12, pady=(12, 6))

    filter_bar = ttk.Frame(top)
    filter_bar.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar(value="")
    template_filter_var = tk.StringVar(value="(wszystkie)")
    ttk.Label(filter_bar, text="Filtr:").pack(side="left")
    ttk.Entry(filter_bar, textvariable=filter_var, width=32).pack(side="left", padx=(6, 8))
    ttk.Label(filter_bar, text="Wzorzec:").pack(side="left", padx=(8, 0))
    template_filter = ttk.Combobox(
        filter_bar,
        textvariable=template_filter_var,
        state="readonly",
        width=28,
    )
    template_filter.pack(side="left", padx=(6, 8))
    count_var = tk.StringVar(value="(ładowanie...)")
    ttk.Label(filter_bar, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="Pobieram produkty z Shopify...")
    ttk.Label(filter_bar, textvariable=progress_var, foreground="#444").pack(side="right")

    table_frame = ttk.Frame(top)
    table_frame.pack(fill="both", expand=True)
    cols = ("artist", "painting_title", "handle", "template_label")
    headings = {
        "artist": "Artysta",
        "painting_title": "Tytuł obrazu",
        "handle": "Handle",
        "template_label": "Wzorzec szablonu",
    }
    widths = {
        "artist": 190,
        "painting_title": 320,
        "handle": 160,
        "template_label": 220,
    }
    sort_state: dict[str, bool] = {}

    tree = ttk.Treeview(
        table_frame,
        columns=cols,
        show="headings",
        height=14,
        selectmode="extended",
    )

    def _make_sort_handler(col: str):
        def handler() -> None:
            reverse = sort_state.get(col, False)
            state["sort_col"] = col
            state["sort_reverse"] = reverse
            sort_state.clear()
            sort_state[col] = not reverse
            _update_sort_headings(active=col, reverse=reverse)
            _refresh_tree()

        return handler

    def _update_sort_headings(*, active: str | None = None, reverse: bool = False) -> None:
        arrow_up = " \u25b2"
        arrow_down = " \u25bc"
        for c in cols:
            base = headings[c]
            if c == active:
                base += arrow_down if reverse else arrow_up
            tree.heading(c, text=base, command=_make_sort_handler(c))

    _update_sort_headings(active="artist", reverse=False)
    for c in cols:
        tree.column(c, width=widths[c], anchor="w", stretch=(c == "painting_title"))
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    row_by_iid: dict[str, dict[str, Any]] = {}

    assign_frame = ttk.LabelFrame(host, text="Przypisz wzorzec szablonu", padding=(10, 8))
    assign_frame.pack(fill="x", padx=12, pady=(0, 12))

    assign_row = ttk.Frame(assign_frame)
    assign_row.pack(fill="x")

    ttk.Label(assign_row, text="Wzorzec szablonu").pack(side="left")
    template_pick_var = tk.StringVar(value="")
    template_pick = ttk.Combobox(
        assign_row,
        textvariable=template_pick_var,
        state="readonly",
        width=34,
    )
    template_pick.pack(side="left", padx=(10, 6))

    preview_btn = ttk.Button(assign_row, text="👁", width=3, command=lambda: _preview_selected())
    preview_btn.pack(side="left", padx=(0, 10))

    apply_btn = ttk.Button(
        assign_row,
        text="Zastosuj do zaznaczonych",
        command=lambda: _apply_template(),
        state="disabled",
    )
    apply_btn.pack(side="left")
    reload_btn = ttk.Button(assign_row, text="Odśwież listę", command=lambda: _load_catalog())
    reload_btn.pack(side="left", padx=(8, 0))

    selection_var = tk.StringVar(
        value="Zaznacz produkt(y). Lista wzorców pochodzi z plików templates/product*.json w repo motywu."
    )
    ttk.Label(assign_frame, textvariable=selection_var, foreground="#444", wraplength=1180).pack(
        anchor="w", pady=(8, 0)
    )
    hint = ttk.Label(
        assign_frame,
        text=(
            "Odpowiednik pola «Wzorzec szablonu» w edytorze produktu Shopify (template_suffix). "
            "Nowe pliki templates/product.<nazwa>.json w motywie pojawią się po odświeżeniu listy."
        ),
        foreground="#666",
        wraplength=1180,
        justify="left",
    )
    hint.pack(anchor="w", pady=(4, 0))

    def _set_busy(busy: bool) -> None:
        state["busy"] = busy
        apply_btn.configure(state="disabled" if busy else ("normal" if tree.selection() else "disabled"))
        reload_btn.configure(state="disabled" if busy else "normal")
        template_pick.configure(state="disabled" if busy else "readonly")
        template_filter.configure(state="disabled" if busy else "readonly")

    def _rebuild_template_combos(templates: list[dict[str, str]]) -> None:
        state["templates"] = templates
        labels = [t["label"] for t in templates]
        suffix_by_label = {t["label"]: t["suffix"] for t in templates}
        label_by_suffix = {t["suffix"]: t["label"] for t in templates}
        state["suffix_by_label"] = suffix_by_label
        state["label_by_suffix"] = label_by_suffix

        template_pick["values"] = labels
        template_filter["values"] = ["(wszystkie)"] + labels
        if labels and not template_pick_var.get():
            template_pick_var.set(labels[0])

    def _filtered_rows() -> list[dict[str, Any]]:
        q = (filter_var.get() or "").strip().lower()
        tpl_filter = (template_filter_var.get() or "(wszystkie)").strip()
        rows = sort_catalog_rows(
            state["rows"],
            col=state["sort_col"],
            reverse=state["sort_reverse"],
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            if tpl_filter and tpl_filter != "(wszystkie)":
                if (r.get("template_label") or "") != tpl_filter:
                    continue
            if q:
                blob = " ".join(
                    str(r.get(k) or "")
                    for k in ("artist", "painting_title", "handle", "product_title", "template_label")
                ).lower()
                if q not in blob:
                    continue
            out.append(r)
        return out

    def _refresh_tree(*, keep_selection: bool = False) -> None:
        selected_pids: set[int] = set()
        if keep_selection:
            for iid in tree.selection():
                row = row_by_iid.get(iid)
                if row:
                    selected_pids.add(int(row.get("product_id") or 0))

        tree.delete(*tree.get_children())
        row_by_iid.clear()
        visible = _filtered_rows()
        restore_iids: list[str] = []
        for r in visible:
            iid = tree.insert(
                "",
                "end",
                values=(
                    r.get("artist") or "",
                    r.get("painting_title") or "",
                    r.get("handle") or "",
                    r.get("template_label") or template_display_label(""),
                ),
            )
            row_by_iid[iid] = r
            if keep_selection and int(r.get("product_id") or 0) in selected_pids:
                restore_iids.append(iid)
        if restore_iids:
            tree.selection_set(restore_iids)
        count_var.set(f"{len(visible)} / {len(state['rows'])} produktów")
        _on_selection_changed()

    filter_var.trace_add("write", lambda *_: _refresh_tree())
    template_filter_var.trace_add("write", lambda *_: _refresh_tree())

    def _on_selection_changed(*_args: object) -> None:
        if state["busy"]:
            return
        sel = tree.selection()
        apply_btn.configure(state="normal" if sel else "disabled")
        if not sel:
            selection_var.set("Zaznacz produkt(y) z listy, wybierz wzorzec i kliknij «Zastosuj».")
            return

        rows = [row_by_iid[iid] for iid in sel if iid in row_by_iid]
        suffixes = {(r.get("template_suffix") or "") for r in rows}
        label_by_suffix = state.get("label_by_suffix") or {}
        if len(suffixes) == 1:
            only = next(iter(suffixes))
            template_pick_var.set(label_by_suffix.get(only, template_display_label(only)))
        n = len(rows)
        if n == 1:
            r = rows[0]
            selection_var.set(
                f"Zaznaczono: {r.get('artist') or ''} — {r.get('painting_title') or ''} "
                f"(obecnie: {r.get('template_label') or '—'})"
            )
        else:
            selection_var.set(
                f"Zaznaczono {n} produktów. Wspólny wzorzec ustawia się tylko, gdy wszystkie mają ten sam."
            )

    tree.bind("<<TreeviewSelect>>", _on_selection_changed)

    def _selected_product_ids() -> list[int]:
        out: list[int] = []
        for iid in tree.selection():
            row = row_by_iid.get(iid)
            if not row:
                continue
            pid = int(row.get("product_id") or 0)
            if pid:
                out.append(pid)
        return out

    def _preview_selected() -> None:
        sel = tree.selection()
        if not sel:
            messagebox.showinfo(APP_TITLE, "Zaznacz produkt, aby otworzyć podgląd strony.", parent=host)
            return
        row = row_by_iid.get(sel[0])
        if not row:
            return
        handle = (row.get("handle") or "").strip()
        url = product_storefront_url(handle) or (row.get("admin_url") or "").strip()
        if url:
            webbrowser.open(url)

    def _apply_template() -> None:
        pids = _selected_product_ids()
        if not pids:
            return
        label = (template_pick_var.get() or "").strip()
        suffix_by_label = state.get("suffix_by_label") or {}
        if label not in suffix_by_label:
            messagebox.showerror(APP_TITLE, "Wybierz wzorzec z listy.", parent=host)
            return
        suffix = suffix_by_label[label]

        if not messagebox.askyesno(
            APP_TITLE,
            f"Ustawić wzorzec «{label}» dla {len(pids)} produkt(ów) w Shopify?",
            parent=host,
        ):
            return

        selected_set = set(pids)

        def worker() -> None:
            def on_progress(msg: str) -> None:
                host.after(0, lambda m=msg: progress_var.set(m))

            result = apply_template_suffix_batch(
                pids,
                suffix,
                on_progress=on_progress,
            )
            host.after(0, lambda: _apply_done(result, suffix, label, selected_set))

        _set_busy(True)
        progress_var.set("Zapisuję w Shopify...")
        threading.Thread(target=worker, daemon=True).start()

    def _apply_done(
        result: dict[str, Any],
        suffix: str,
        label: str,
        selected_set: set[int],
    ) -> None:
        _set_busy(False)
        updated = int(result.get("updated") or 0)
        errors = result.get("errors") or []
        failed_pids: set[int] = set()
        for err in errors:
            text = str(err)
            if text.startswith("Produkt "):
                head = text.split(":", 1)[0]
                try:
                    failed_pids.add(int(head.replace("Produkt ", "").strip()))
                except ValueError:
                    pass

        for row in state["rows"]:
            pid = int(row.get("product_id") or 0)
            if pid in selected_set and pid not in failed_pids:
                row["template_suffix"] = suffix
                row["template_label"] = label

        _refresh_tree(keep_selection=True)
        progress_var.set(f"Zapisano wzorzec dla {updated} produkt(ów).")
        if errors:
            messagebox.showwarning(
                APP_TITLE,
                f"Zaktualizowano {updated} z {len(selected_set)}.\n\n" + "\n".join(errors[:8]),
                parent=host,
            )
        else:
            show_toast(host, f"Wzorzec «{label}» — {updated} produkt(ów)")

    def _load_catalog() -> None:
        def worker() -> None:
            def on_progress(msg: str) -> None:
                host.after(0, lambda m=msg: progress_var.set(m))

            rows, templates = load_catalog_with_template_suffix(on_progress=on_progress)
            host.after(0, lambda: _catalog_loaded(rows, templates))

        _set_busy(True)
        progress_var.set("Pobieram produkty z Shopify...")
        threading.Thread(target=worker, daemon=True).start()

    def _catalog_loaded(rows: list[dict[str, Any]], templates: list[dict[str, str]]) -> None:
        _set_busy(False)
        state["rows"] = rows
        _rebuild_template_combos(templates)
        _refresh_tree()
        progress_var.set(f"Gotowe — {len(rows)} produktów, {len(templates)} wzorców.")

    _load_catalog()
