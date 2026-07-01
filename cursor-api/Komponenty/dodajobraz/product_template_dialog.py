"""Okno «Wybór szablonu produktu» — lista produktow i przypisanych szablonow wariantow."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from . import shopify_client as sc
from . import templates as variant_templates
from .description_update import load_product_catalog_rows, product_catalog_sort_key
from .product_template_assignments import (
    set_product_template_assignments_batch,
    template_label_for_product,
)


def open_product_template_dialog(
    parent: tk.Misc,
    *,
    enqueue_log: Callable[[str], None] | None = None,
    set_status: Callable[[str], None] | None = None,
    standalone: bool = False,
) -> tk.Toplevel:
    dlg = tk.Toplevel(parent) if not standalone else parent
    dlg.title("Wybór szablonu produktu")
    position_toplevel_screen_center(dlg, 1180, 720)
    dlg.minsize(980, 560)
    if not standalone:
        try:
            dlg.transient(parent.winfo_toplevel())
        except (tk.TclError, AttributeError):
            pass

    def _log(msg: str) -> None:
        if enqueue_log:
            try:
                enqueue_log(msg)
            except Exception:  # noqa: BLE001
                pass

    def _status(msg: str) -> None:
        if set_status:
            try:
                set_status(msg)
            except Exception:  # noqa: BLE001
                pass

    root = ttk.Frame(dlg, padding=8)
    root.pack(fill="both", expand=True)

    paned = ttk.Panedwindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True)

    state: dict[str, Any] = {
        "rows": [],
        "variants_by_pid": {},
        "templates": variant_templates.load_templates(),
        "selected_template_id": None,
        "sort_col": "artist",
        "sort_reverse": False,
    }

    # --- lewa: produkty ---
    left = ttk.LabelFrame(paned, text="Produkty (Ctrl+klik — wiele zaznaczen)", padding=6)
    paned.add(left, weight=3)

    filter_row = ttk.Frame(left)
    filter_row.pack(fill="x", pady=(0, 6))
    filter_var = tk.StringVar()
    ttk.Label(filter_row, text="Filtr:").pack(side="left")
    ttk.Entry(filter_row, textvariable=filter_var, width=36).pack(side="left", padx=(6, 8))
    count_var = tk.StringVar(value="—")
    ttk.Label(filter_row, textvariable=count_var, foreground="#0a6").pack(side="left")
    progress_var = tk.StringVar(value="")
    ttk.Label(filter_row, textvariable=progress_var, foreground="#666").pack(side="right")

    table_frame = ttk.Frame(left)
    table_frame.pack(fill="both", expand=True)
    cols = ("artist", "painting_title", "handle", "template")
    headings = {
        "artist": "Artysta",
        "painting_title": "Tytul obrazu",
        "handle": "Handle",
        "template": "Szablon",
    }
    widths = {"artist": 180, "painting_title": 280, "handle": 140, "template": 200}
    sort_state: dict[str, bool] = {}

    tree = ttk.Treeview(
        table_frame,
        columns=cols,
        show="headings",
        height=16,
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
            _refresh_products()

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
        anchor = "w" if c != "template" else "w"
        tree.column(c, width=widths[c], anchor=anchor, stretch=(c == "painting_title"))
    tree.tag_configure("assigned", foreground="#1b5e20")
    tree.tag_configure("inferred", foreground="#555")
    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    prod_btns = ttk.Frame(left)
    prod_btns.pack(fill="x", pady=(6, 0))
    refresh_btn = ttk.Button(prod_btns, text="Odswiez liste")
    refresh_btn.pack(side="left")
    assign_btn = ttk.Button(prod_btns, text="Przypisz wybrany szablon", state="disabled")
    assign_btn.pack(side="left", padx=(8, 0))
    apply_btn = ttk.Button(prod_btns, text="Zastosuj w Shopify", state="disabled")
    apply_btn.pack(side="left", padx=(8, 0))

    # --- prawa: szablony ---
    right = ttk.LabelFrame(paned, text="Szablony wariantow", padding=6)
    paned.add(right, weight=1)

    tpl_list_wrap = ttk.Frame(right)
    tpl_list_wrap.pack(fill="both", expand=True)
    tpl_lb = tk.Listbox(tpl_list_wrap, height=14, exportselection=False, activestyle="none")
    tpl_lb.pack(side="left", fill="both", expand=True)
    tpl_sb = ttk.Scrollbar(tpl_list_wrap, command=tpl_lb.yview)
    tpl_sb.pack(side="right", fill="y")
    tpl_lb.configure(yscrollcommand=tpl_sb.set)

    name_row = ttk.Frame(right)
    name_row.pack(fill="x", pady=(8, 4))
    ttk.Label(name_row, text="Nazwa:").pack(side="left")
    tpl_name_var = tk.StringVar()
    tpl_name_entry = ttk.Entry(name_row, textvariable=tpl_name_var, width=28)
    tpl_name_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))

    tpl_btns1 = ttk.Frame(right)
    tpl_btns1.pack(fill="x", pady=2)
    save_name_btn = ttk.Button(tpl_btns1, text="Zapisz nazwe", state="disabled")
    save_name_btn.pack(side="left")
    tpl_btns2 = ttk.Frame(right)
    tpl_btns2.pack(fill="x", pady=2)
    new_btn = ttk.Button(tpl_btns2, text="+ Nowy pusty")
    new_btn.pack(side="left", padx=(0, 4))
    dup_btn = ttk.Button(tpl_btns2, text="Kopiuj", state="disabled")
    dup_btn.pack(side="left", padx=(0, 4))
    shopify_btn = ttk.Button(tpl_btns2, text="+ Z Shopify...")
    shopify_btn.pack(side="left")
    tpl_btns3 = ttk.Frame(right)
    tpl_btns3.pack(fill="x", pady=(6, 0))
    edit_tpl_btn = ttk.Button(tpl_btns3, text="Edytuj warianty (Szablony...)")
    edit_tpl_btn.pack(side="left")

    filter_var.trace_add("write", lambda *_: _refresh_products())

    def _selected_pids() -> list[int]:
        pids: list[int] = []
        for iid in tree.selection():
            try:
                pids.append(int(iid))
            except (TypeError, ValueError):
                continue
        return pids

    def _selected_template_id() -> str | None:
        sel = tpl_lb.curselection()
        if not sel:
            return None
        idx = sel[0]
        if idx < 0 or idx >= len(state["templates"]):
            return None
        return state["templates"][idx].id

    def _refresh_template_list(*, select_id: str | None = None) -> None:
        state["templates"] = variant_templates.load_templates()
        tpl_lb.delete(0, "end")
        select_idx = 0
        for i, t in enumerate(state["templates"]):
            suffix = " *" if t.is_default else ""
            tpl_lb.insert("end", f"{t.name}{suffix}")
            if select_id and t.id == select_id:
                select_idx = i
        if state["templates"]:
            tpl_lb.selection_set(select_idx)
            tpl_lb.see(select_idx)
            _on_template_select()
        else:
            tpl_name_var.set("")
            save_name_btn.configure(state="disabled")
            dup_btn.configure(state="disabled")

    def _on_template_select(_event: tk.Event | None = None) -> None:
        tid = _selected_template_id()
        state["selected_template_id"] = tid
        t = variant_templates.get_by_id(tid) if tid else None
        if t:
            tpl_name_var.set(t.name)
            save_name_btn.configure(state="normal")
            dup_btn.configure(state="normal")
        else:
            tpl_name_var.set("")
            save_name_btn.configure(state="disabled")
            dup_btn.configure(state="disabled")
        _update_action_btns()

    def _update_action_btns() -> None:
        n = len(_selected_pids())
        tid = _selected_template_id()
        if n and tid:
            assign_btn.configure(state="normal", text=f"Przypisz szablon ({n})")
            apply_btn.configure(state="normal", text=f"Zastosuj w Shopify ({n})")
        else:
            assign_btn.configure(state="disabled", text="Przypisz wybrany szablon")
            apply_btn.configure(state="disabled", text="Zastosuj w Shopify")

    def _product_sort_key(row: dict[str, Any]) -> tuple:
        pid = int(row.get("product_id") or 0)
        variants = state["variants_by_pid"].get(pid) or []
        label, _tid, explicit = template_label_for_product(pid, variants=variants)
        col = state.get("sort_col") or "artist"
        surname = (row.get("surname") or "").strip().lower()
        firstname = (row.get("firstname") or "").strip().lower()
        painting = (row.get("painting_title") or "").strip().lower()
        handle = (row.get("handle") or "").strip().lower()
        if col == "template":
            return (label.lower(), surname, firstname, painting, handle)
        if col == "artist":
            return (*product_catalog_sort_key(row), handle)
        if col == "painting_title":
            return (painting, surname, firstname, handle)
        if col == "handle":
            return (handle, surname, firstname, painting)
        return (surname, firstname, painting, handle)

    def _refresh_products(*, preserve_pids: set[int] | None = None) -> None:
        keep = set(preserve_pids or ()) or set(_selected_pids())
        tree.delete(*tree.get_children())
        q = filter_var.get().strip().lower()
        visible: list[dict[str, Any]] = []
        for row in state["rows"]:
            blob = " ".join(
                [
                    str(row.get("surname") or ""),
                    str(row.get("firstname") or ""),
                    str(row.get("artist") or ""),
                    str(row.get("painting_title") or ""),
                    str(row.get("handle") or ""),
                ]
            ).lower()
            pid = int(row.get("product_id") or 0)
            variants = state["variants_by_pid"].get(pid) or []
            tpl_label, _tid, explicit = template_label_for_product(pid, variants=variants)
            if q and q not in blob and q not in tpl_label.lower():
                continue
            visible.append(row)

        visible.sort(key=_product_sort_key, reverse=bool(state.get("sort_reverse")))
        selected: list[str] = []
        for row in visible:
            pid = int(row.get("product_id") or 0)
            variants = state["variants_by_pid"].get(pid) or []
            tpl_label, _tid, explicit = template_label_for_product(pid, variants=variants)
            tags = ("assigned",) if explicit else ("inferred",)
            iid = str(pid)
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("artist", ""),
                    row.get("painting_title", ""),
                    row.get("handle", ""),
                    tpl_label,
                ),
                tags=tags,
            )
            if pid in keep:
                selected.append(iid)
        if selected:
            tree.selection_set(selected)
            tree.see(selected[0])
        count_var.set(f"Widocznych: {len(visible)}/{len(state['rows'])}")
        _update_action_btns()

    def _load_products() -> None:
        refresh_btn.configure(state="disabled")
        progress_var.set("Ladowanie...")

        def work() -> None:
            try:
                rows = load_product_catalog_rows(
                    logger=_log,
                    on_progress=lambda m: dlg.after(0, lambda msg=m: progress_var.set(msg)),
                )
                shop, token = sc.load_session()
                dlg.after(0, lambda: progress_var.set("Pobieram warianty produktow..."))
                products = sc.fetch_all_products(
                    shop,
                    token,
                    product_type="Obraz",
                    fields="id,variants",
                    on_page_progress=lambda n: dlg.after(
                        0,
                        lambda c=n: progress_var.set(f"Warianty: {c} produktow..."),
                    ),
                )
                variants_by_pid: dict[int, list[dict[str, Any]]] = {
                    int(p.get("id") or 0): list(p.get("variants") or [])
                    for p in products
                    if int(p.get("id") or 0) > 0
                }
            except Exception as exc:  # noqa: BLE001
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror(
                        "Blad",
                        str(e),
                        parent=dlg,
                    ),
                )
                dlg.after(0, lambda: progress_var.set("Blad pobierania."))
                dlg.after(0, lambda: refresh_btn.configure(state="normal"))
                return

            def done() -> None:
                state["rows"] = rows
                state["variants_by_pid"] = variants_by_pid
                _refresh_products()
                progress_var.set(f"Gotowe — {len(rows)} produkt(ow).")
                refresh_btn.configure(state="normal")
                _status(f"Wybór szablonu: {len(rows)} produktow.")

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True, name="load-product-templates").start()

    def _assign_template() -> None:
        pids = _selected_pids()
        tid = _selected_template_id()
        if not pids or not tid:
            return
        t = variant_templates.get_by_id(tid)
        if not t:
            messagebox.showerror("Blad", "Nie znaleziono szablonu.", parent=dlg)
            return
        n = set_product_template_assignments_batch(pids, tid)
        _refresh_products(preserve_pids=set(pids))
        show_toast(dlg, f"Przypisano «{t.name}» do {n} produkt(ow)", duration_ms=1600)

    def _apply_to_shopify() -> None:
        pids = _selected_pids()
        tid = _selected_template_id()
        if not pids or not tid:
            return
        t = variant_templates.get_by_id(tid)
        if not t:
            messagebox.showerror("Blad", "Nie znaleziono szablonu.", parent=dlg)
            return
        try:
            variant_templates.validate_template_for_existing_products(t)
        except sc.ShopifyError as e:
            messagebox.showerror("Nie mozna zastosowac", str(e), parent=dlg)
            return
        if not messagebox.askyesno(
            "Zastosuj szablon w Shopify",
            f"Zastosowac szablon «{t.name}» do {len(pids)} produkt(ow)?\n\n"
            "Operacja moze tworzyc brakujace warianty, aktualizowac ceny "
            "i usuwac warianty spoza szablonu.",
            parent=dlg,
        ):
            return
        apply_btn.configure(state="disabled")
        progress_var.set("Stosowanie szablonu...")

        def work() -> None:
            try:
                summary = variant_templates.apply_template_to_product_ids(
                    tid,
                    pids,
                    logger=_log,
                    on_progress=lambda m: dlg.after(0, lambda msg=m: progress_var.set(msg)),
                )
                set_product_template_assignments_batch(pids, tid)
            except Exception as exc:  # noqa: BLE001
                dlg.after(
                    0,
                    lambda e=exc: messagebox.showerror("Blad", str(e), parent=dlg),
                )
                dlg.after(0, lambda: progress_var.set("Blad."))
                dlg.after(0, _update_action_btns)
                return

            errors = summary.get("errors") or []
            msg = (
                f"Zastosowano do {summary.get('products_updated', 0)}/"
                f"{summary.get('products_total', 0)} produktow.\n"
                f"Bledy: {len(errors)}"
            )
            if errors:
                msg += "\n\n" + "\n".join(str(e) for e in errors[:5])

            def done() -> None:
                _refresh_products(preserve_pids=set(pids))
                progress_var.set("Gotowe.")
                _update_action_btns()
                messagebox.showinfo("Gotowe", msg, parent=dlg)

            dlg.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _save_template_name() -> None:
        tid = _selected_template_id()
        if not tid:
            return
        name = tpl_name_var.get().strip()
        if not name:
            messagebox.showwarning("Nazwa", "Podaj nazwe szablonu.", parent=dlg)
            return
        updated = variant_templates.update_template(tid, name=name)
        if not updated:
            messagebox.showerror("Blad", "Nie zapisano nazwy.", parent=dlg)
            return
        _refresh_template_list(select_id=tid)
        _refresh_products(preserve_pids=set(_selected_pids()))
        show_toast(dlg, f"Zapisano nazwe: {name}", duration_ms=1400)

    def _new_empty_template() -> None:
        name = simpledialog.askstring("Nowy szablon", "Nazwa szablonu:", parent=dlg)
        if not name:
            return
        new_t = variant_templates.VariantTemplate.new(
            name=name.strip(),
            options=[],
            variants=[],
            source="manual",
            is_default=False,
        )
        variant_templates.add_template(new_t)
        _refresh_template_list(select_id=new_t.id)
        show_toast(dlg, f"Utworzono: {name.strip()}")

    def _duplicate_template() -> None:
        tid = _selected_template_id()
        if not tid:
            return
        src = variant_templates.get_by_id(tid)
        if not src:
            return
        name = simpledialog.askstring(
            "Kopiuj szablon",
            "Nazwa kopii:",
            initialvalue=f"{src.name} (kopia)",
            parent=dlg,
        )
        if not name:
            return
        copy = variant_templates.duplicate_template(tid, new_name=name.strip())
        if not copy:
            messagebox.showerror("Blad", "Nie udalo sie skopiowac szablonu.", parent=dlg)
            return
        _refresh_template_list(select_id=copy.id)
        show_toast(dlg, f"Skopiowano: {copy.name}", duration_ms=1400)

    def _new_from_shopify() -> None:
        pid_str = simpledialog.askstring(
            "Nowy szablon z Shopify",
            "ID produktu:",
            parent=dlg,
        )
        if not pid_str:
            return
        try:
            pid = int(pid_str.strip())
        except ValueError:
            messagebox.showerror("Blad", "ID musi byc liczba.", parent=dlg)
            return
        name = simpledialog.askstring(
            "Nowy szablon z Shopify",
            "Nazwa (puste = auto):",
            parent=dlg,
        )
        try:
            new_t = variant_templates.import_from_shopify(pid, name=name.strip() if name else None)
        except sc.ShopifyError as e:
            messagebox.showerror("Blad", str(e), parent=dlg)
            return
        _refresh_template_list(select_id=new_t.id)
        show_toast(dlg, f"Zaimportowano: {new_t.name}", duration_ms=1600)

    def _open_templates_editor() -> None:
        from .templates_dialog import open_templates_dialog

        open_templates_dialog(dlg)
        _refresh_template_list(select_id=_selected_template_id())
        _refresh_products(preserve_pids=set(_selected_pids()))

    refresh_btn.configure(command=_load_products)
    assign_btn.configure(command=_assign_template)
    apply_btn.configure(command=_apply_to_shopify)
    save_name_btn.configure(command=_save_template_name)
    new_btn.configure(command=_new_empty_template)
    dup_btn.configure(command=_duplicate_template)
    shopify_btn.configure(command=_new_from_shopify)
    edit_tpl_btn.configure(command=_open_templates_editor)
    tpl_lb.bind("<<ListboxSelect>>", _on_template_select)
    tree.bind("<<TreeviewSelect>>", lambda _e: _update_action_btns())

    _refresh_template_list()
    dlg.after(100, _load_products)
    return dlg
