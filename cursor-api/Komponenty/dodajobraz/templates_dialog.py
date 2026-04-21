"""Dialog 'Szablony wariantow' - CRUD dla `variant_templates.json`.

Uzycie z gui.py:
    from .templates_dialog import open_templates_dialog
    open_templates_dialog(parent)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from . import shopify_client as sc
from . import templates as variant_templates

try:
    from Komponenty._shared.toast import show_toast
except ImportError:  # pragma: no cover
    def show_toast(parent: tk.Misc, text: str, **_kw) -> None:  # type: ignore[override]
        print(f"[toast] {text}")


# Pola wariantow w edytowanej tabeli
_VARIANT_COLS: list[tuple[str, str, int]] = [
    ("option1", "Opcja 1", 140),
    ("option2", "Opcja 2", 140),
    ("option3", "Opcja 3", 140),
    ("price", "Cena", 80),
    ("compare_at_price", "Cena por.", 80),
    ("weight", "Waga", 60),
    ("weight_unit", "Jedn.", 50),
    ("inventory_policy", "Polityka", 80),
]


def open_templates_dialog(parent: tk.Misc) -> tk.Toplevel:
    dlg = tk.Toplevel(parent)
    dlg.title("Szablony wariantow")
    dlg.geometry("1180x720")
    dlg.minsize(980, 560)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass
    dlg.grab_set()

    root = ttk.Frame(dlg, padding=8)
    root.pack(fill="both", expand=True)

    paned = ttk.Panedwindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True)

    # ------------------ LEWA: lista szablonow ------------------
    left = ttk.LabelFrame(paned, text="Szablony")
    paned.add(left, weight=1)

    list_wrap = ttk.Frame(left)
    list_wrap.pack(fill="both", expand=True, padx=4, pady=4)
    lb = tk.Listbox(list_wrap, height=20, exportselection=False, activestyle="none")
    lb.pack(side="left", fill="both", expand=True)
    sb_l = ttk.Scrollbar(list_wrap, command=lb.yview)
    sb_l.pack(side="right", fill="y")
    lb.configure(yscrollcommand=sb_l.set)

    left_btns = ttk.Frame(left)
    left_btns.pack(fill="x", padx=4, pady=(0, 4))
    # Przyciski dodawania
    for btn_label, btn_cmd_name in [
        ("+ Nowy pusty", "new_empty"),
        ("+ Z Shopify...", "new_from_shopify"),
        ("Duplikuj", "duplicate"),
        ("Usun", "delete"),
        ("Domyslny", "set_default"),
    ]:
        # Stub - zostaje podmieniony nizej (potrzebujemy domykniec nad state)
        ttk.Button(left_btns, text=btn_label, name=btn_cmd_name).pack(side="left", padx=1)

    # ------------------ PRAWA: edycja szablonu ------------------
    right = ttk.Frame(paned)
    paned.add(right, weight=3)

    # Naglowek szablonu: nazwa + source + isDefault
    head = ttk.Frame(right)
    head.pack(fill="x", pady=(0, 4))
    ttk.Label(head, text="Nazwa szablonu:").pack(side="left")
    name_var = tk.StringVar()
    ttk.Entry(head, textvariable=name_var, width=32, font=("Segoe UI", 10, "bold")).pack(
        side="left", padx=(6, 0)
    )
    ttk.Label(head, text="Zrodlo:").pack(side="left", padx=(18, 6))
    source_var = tk.StringVar()
    source_lbl = ttk.Label(head, textvariable=source_var, foreground="#666")
    source_lbl.pack(side="left")

    is_default_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        head, text="Szablon domyslny (uzywany przy tworzeniu nowego produktu)",
        variable=is_default_var,
    ).pack(side="right")

    # Opcje produktu (list of {name, values, position})
    opt_frame = ttk.LabelFrame(right, text="Opcje (np. 'Rozmiar', 'Rodzaj drewna')")
    opt_frame.pack(fill="x", pady=4)
    opt_tree = ttk.Treeview(
        opt_frame, columns=("name", "values", "position"),
        show="headings", height=4,
    )
    opt_tree.heading("name", text="Nazwa")
    opt_tree.heading("values", text="Dopuszczalne wartosci (oddziel przecinkiem)")
    opt_tree.heading("position", text="Poz.")
    opt_tree.column("name", width=160)
    opt_tree.column("values", width=520)
    opt_tree.column("position", width=50, anchor="center")
    opt_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)

    opt_btns = ttk.Frame(opt_frame)
    opt_btns.pack(side="right", fill="y", padx=4, pady=4)
    ttk.Button(opt_btns, text="+ Opcja", name="opt_add").pack(fill="x", pady=2)
    ttk.Button(opt_btns, text="Edytuj", name="opt_edit").pack(fill="x", pady=2)
    ttk.Button(opt_btns, text="Usun", name="opt_del").pack(fill="x", pady=2)

    # Warianty (tabela)
    var_frame = ttk.LabelFrame(right, text="Warianty (kombinacje opcji + ceny)")
    var_frame.pack(fill="both", expand=True, pady=4)
    var_tree = ttk.Treeview(
        var_frame,
        columns=[c[0] for c in _VARIANT_COLS],
        show="headings", height=16,
    )
    for col, label, width in _VARIANT_COLS:
        var_tree.heading(col, text=label)
        var_tree.column(col, width=width, anchor="w")
    var_tree.pack(side="left", fill="both", expand=True, padx=4, pady=4)
    sb_v = ttk.Scrollbar(var_frame, command=var_tree.yview)
    sb_v.pack(side="left", fill="y", pady=4)
    var_tree.configure(yscrollcommand=sb_v.set)

    var_btns = ttk.Frame(var_frame)
    var_btns.pack(side="right", fill="y", padx=4, pady=4)
    ttk.Button(var_btns, text="+ Wariant", name="var_add").pack(fill="x", pady=2)
    ttk.Button(var_btns, text="Edytuj", name="var_edit").pack(fill="x", pady=2)
    ttk.Button(var_btns, text="Usun", name="var_del").pack(fill="x", pady=2)
    ttk.Button(var_btns, text="Generuj z opcji", name="var_gen").pack(fill="x", pady=(10, 2))

    # Pasek akcji dolny (zapis / odswiez / zamknij)
    bottom = ttk.Frame(root)
    bottom.pack(fill="x", pady=(8, 0))
    ttk.Label(bottom, text="", foreground="#888").pack(side="left")
    ttk.Button(bottom, text="Zamknij", command=dlg.destroy).pack(side="right")
    ttk.Button(bottom, text="Zapisz zmiany", name="save_btn").pack(side="right", padx=(0, 6))
    ttk.Button(bottom, text="Odswiez z Shopify...", name="refresh_btn").pack(side="right", padx=(0, 6))

    # -------- Stan dialogu --------
    state: dict[str, Any] = {
        "templates": variant_templates.load_templates(),
        "selected_id": None,
        "dirty": False,
    }

    # -------- Helpers --------
    def mark_dirty(*_args) -> None:
        state["dirty"] = True

    name_var.trace_add("write", mark_dirty)
    source_var.trace_add("write", mark_dirty)
    is_default_var.trace_add("write", mark_dirty)

    def refresh_left_list(*, select_id: str | None = None) -> None:
        lb.delete(0, "end")
        for t in state["templates"]:
            marker = " ★" if t.is_default else ""
            lb.insert("end", f"{t.name}{marker}")
        # Zaznacz
        target_id = select_id or state.get("selected_id")
        if target_id:
            for i, t in enumerate(state["templates"]):
                if t.id == target_id:
                    lb.selection_clear(0, "end")
                    lb.selection_set(i)
                    lb.see(i)
                    state["selected_id"] = t.id
                    load_template_into_editor(t)
                    return
        if state["templates"]:
            lb.selection_set(0)
            state["selected_id"] = state["templates"][0].id
            load_template_into_editor(state["templates"][0])
        else:
            clear_editor()

    def clear_editor() -> None:
        state["selected_id"] = None
        name_var.set("")
        source_var.set("")
        is_default_var.set(False)
        for iid in opt_tree.get_children():
            opt_tree.delete(iid)
        for iid in var_tree.get_children():
            var_tree.delete(iid)
        state["dirty"] = False

    def load_template_into_editor(t: variant_templates.VariantTemplate) -> None:
        state["selected_id"] = t.id
        name_var.set(t.name)
        source_var.set(t.source)
        is_default_var.set(t.is_default)
        # Opcje
        for iid in opt_tree.get_children():
            opt_tree.delete(iid)
        for i, opt in enumerate(t.options):
            opt_tree.insert(
                "", "end", iid=str(i),
                values=(
                    opt.get("name") or "",
                    ", ".join(str(v) for v in (opt.get("values") or [])),
                    opt.get("position") or (i + 1),
                ),
            )
        # Warianty
        for iid in var_tree.get_children():
            var_tree.delete(iid)
        for i, v in enumerate(t.variants):
            row_vals = tuple(str(v.get(c, "") or "") for c, _, _ in _VARIANT_COLS)
            var_tree.insert("", "end", iid=str(i), values=row_vals)
        state["dirty"] = False

    def collect_editor_into_state() -> None:
        """Zbiera dane z UI z powrotem do state['templates'][selected]."""
        tid = state.get("selected_id")
        if not tid:
            return
        for i, t in enumerate(state["templates"]):
            if t.id != tid:
                continue
            t.name = name_var.get().strip() or "(bez nazwy)"
            t.is_default = bool(is_default_var.get())
            # Opcje
            opts: list[dict] = []
            for iid in opt_tree.get_children():
                vals = opt_tree.item(iid, "values")
                opt_name = str(vals[0]).strip()
                values_raw = str(vals[1])
                values = [v.strip() for v in values_raw.split(",") if v.strip()]
                try:
                    position = int(str(vals[2]))
                except (ValueError, TypeError):
                    position = len(opts) + 1
                if opt_name:
                    opts.append({"name": opt_name, "values": values, "position": position})
            t.options = opts
            # Warianty
            variants: list[dict] = []
            for iid in var_tree.get_children():
                vals = var_tree.item(iid, "values")
                entry: dict[str, Any] = {}
                for idx, (col, _lbl, _w) in enumerate(_VARIANT_COLS):
                    raw = str(vals[idx]).strip() if idx < len(vals) else ""
                    if raw:
                        entry[col] = raw
                variants.append(entry)
            t.variants = variants
            state["templates"][i] = t
            break

    # -------- CRUD szablonow (lewa lista) --------
    def on_select_template(_e: tk.Event | None = None) -> None:
        if state["dirty"]:
            if not messagebox.askyesno(
                "Niezapisane zmiany",
                "Masz niezapisane zmiany. Porzucic je?",
                parent=dlg,
            ):
                # Przywroc stare zaznaczenie
                for i, t in enumerate(state["templates"]):
                    if t.id == state.get("selected_id"):
                        lb.selection_clear(0, "end")
                        lb.selection_set(i)
                        return
                return
        sel = lb.curselection()
        if not sel:
            return
        t = state["templates"][sel[0]]
        load_template_into_editor(t)

    lb.bind("<<ListboxSelect>>", on_select_template)

    def new_empty_template() -> None:
        name = simpledialog.askstring(
            "Nowy szablon",
            "Nazwa szablonu:",
            parent=dlg,
        )
        if not name:
            return
        new_t = variant_templates.VariantTemplate.new(
            name=name,
            options=[],
            variants=[],
            source="manual",
            is_default=False,
        )
        state["templates"].append(new_t)
        variant_templates.save_templates(state["templates"])
        refresh_left_list(select_id=new_t.id)
        show_toast(dlg, f"Utworzono: {name}")

    def new_from_shopify_template() -> None:
        pid_str = simpledialog.askstring(
            "Nowy szablon z produktu Shopify",
            "ID produktu (np. 15524677845340):",
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
            "Nowy szablon z produktu Shopify",
            "Nazwa szablonu (puste = auto z produktu):",
            parent=dlg,
        )
        try:
            new_t = variant_templates.fetch_template_from_shopify(pid, name=name or None)
        except (sc.ShopifyError, FileNotFoundError, OSError) as e:
            messagebox.showerror("Blad", f"Nie udalo sie pobrac z Shopify:\n{e}", parent=dlg)
            return
        state["templates"].append(new_t)
        variant_templates.save_templates(state["templates"])
        refresh_left_list(select_id=new_t.id)
        show_toast(dlg, f"Zaimportowano: {new_t.name}")

    def duplicate_template() -> None:
        tid = state.get("selected_id")
        if not tid:
            return
        new_t = variant_templates.duplicate_template(tid)
        if new_t:
            state["templates"] = variant_templates.load_templates()
            refresh_left_list(select_id=new_t.id)
            show_toast(dlg, "Zduplikowano szablon")

    def delete_template() -> None:
        tid = state.get("selected_id")
        if not tid:
            return
        t = next((x for x in state["templates"] if x.id == tid), None)
        if not t:
            return
        if len(state["templates"]) <= 1:
            messagebox.showwarning(
                "Nie mozna usunac",
                "Musi pozostac przynajmniej jeden szablon.",
                parent=dlg,
            )
            return
        if not messagebox.askyesno(
            "Usun szablon",
            f"Na pewno usunac szablon '{t.name}'?",
            parent=dlg,
        ):
            return
        variant_templates.delete_template(tid)
        state["templates"] = variant_templates.load_templates()
        refresh_left_list()

    def set_default_template() -> None:
        tid = state.get("selected_id")
        if not tid:
            return
        variant_templates.set_default(tid)
        state["templates"] = variant_templates.load_templates()
        refresh_left_list(select_id=tid)
        show_toast(dlg, "Ustawiono jako domyslny")

    def refresh_from_shopify() -> None:
        tid = state.get("selected_id")
        if not tid:
            return
        t = next((x for x in state["templates"] if x.id == tid), None)
        if not t:
            return
        if not t.source.startswith("shopify:"):
            messagebox.showinfo(
                "Odswiez z Shopify",
                "Ten szablon nie pochodzi z Shopify - nic do odswiezenia.",
                parent=dlg,
            )
            return
        try:
            pid = int(t.source.split(":", 1)[1])
        except ValueError:
            messagebox.showerror("Blad", "Nieprawidlowe pole source.", parent=dlg)
            return
        if not messagebox.askyesno(
            "Odswiez z Shopify",
            f"Nadpisac warianty w '{t.name}' danymi z produktu Shopify {pid}?\n"
            f"(Nazwa szablonu i flaga domyslnego zostana zachowane)",
            parent=dlg,
        ):
            return
        try:
            fresh = variant_templates.fetch_template_from_shopify(pid, name=t.name)
        except (sc.ShopifyError, FileNotFoundError, OSError) as e:
            messagebox.showerror("Blad", f"Nie udalo sie pobrac z Shopify:\n{e}", parent=dlg)
            return
        variant_templates.update_template(
            t.id,
            options=fresh.options,
            variants=fresh.variants,
        )
        state["templates"] = variant_templates.load_templates()
        refresh_left_list(select_id=t.id)
        show_toast(dlg, "Odswiezono z Shopify")

    # -------- CRUD opcji (srodkowa tabela) --------
    def opt_add() -> None:
        name = simpledialog.askstring("Nowa opcja", "Nazwa opcji (np. Rozmiar):", parent=dlg)
        if not name:
            return
        values = simpledialog.askstring(
            "Nowa opcja",
            "Wartosci oddzielone przecinkami (np. 50x70, 70x100, 100x140):",
            parent=dlg,
        ) or ""
        position = len(opt_tree.get_children()) + 1
        opt_tree.insert("", "end", values=(name, values, position))
        mark_dirty()

    def opt_edit() -> None:
        sel = opt_tree.selection()
        if not sel:
            return
        iid = sel[0]
        vals = opt_tree.item(iid, "values")
        new_name = simpledialog.askstring("Edytuj opcje", "Nazwa:", initialvalue=vals[0], parent=dlg)
        if new_name is None:
            return
        new_values = simpledialog.askstring(
            "Edytuj opcje", "Wartosci (przecinek):",
            initialvalue=vals[1], parent=dlg,
        )
        if new_values is None:
            return
        opt_tree.item(iid, values=(new_name, new_values, vals[2]))
        mark_dirty()

    def opt_del() -> None:
        for iid in opt_tree.selection():
            opt_tree.delete(iid)
        mark_dirty()

    # -------- CRUD wariantow (tabela) --------
    def _edit_variant_dialog(initial: tuple[str, ...] | None = None) -> tuple[str, ...] | None:
        """Mini-dialog do edycji pol wariantu."""
        vdlg = tk.Toplevel(dlg)
        vdlg.title("Wariant")
        vdlg.geometry("460x420")
        vdlg.transient(dlg)
        vdlg.grab_set()

        frame = ttk.Frame(vdlg, padding=10)
        frame.pack(fill="both", expand=True)
        vars_map: dict[str, tk.StringVar] = {}
        for i, (col, label, _w) in enumerate(_VARIANT_COLS):
            ttk.Label(frame, text=label + ":").grid(row=i, column=0, sticky="w", pady=3)
            sv = tk.StringVar(value=str(initial[i]) if initial else "")
            ttk.Entry(frame, textvariable=sv, width=36).grid(row=i, column=1, sticky="ew", pady=3)
            vars_map[col] = sv
        frame.columnconfigure(1, weight=1)

        result: dict[str, tuple[str, ...] | None] = {"value": None}

        def _save() -> None:
            result["value"] = tuple(vars_map[col].get().strip() for col, _, _ in _VARIANT_COLS)
            vdlg.destroy()

        btns = ttk.Frame(frame)
        btns.grid(row=len(_VARIANT_COLS), column=0, columnspan=2, pady=(10, 0), sticky="e")
        ttk.Button(btns, text="OK", command=_save).pack(side="right")
        ttk.Button(btns, text="Anuluj", command=vdlg.destroy).pack(side="right", padx=(0, 6))
        vdlg.bind("<Return>", lambda _e: _save())
        vdlg.bind("<Escape>", lambda _e: vdlg.destroy())
        vdlg.wait_window()
        return result["value"]

    def var_add() -> None:
        result = _edit_variant_dialog()
        if result is None:
            return
        var_tree.insert("", "end", values=result)
        mark_dirty()

    def var_edit() -> None:
        sel = var_tree.selection()
        if not sel:
            return
        iid = sel[0]
        initial = tuple(str(x) for x in var_tree.item(iid, "values"))
        result = _edit_variant_dialog(initial=initial)
        if result is None:
            return
        var_tree.item(iid, values=result)
        mark_dirty()

    def var_del() -> None:
        for iid in var_tree.selection():
            var_tree.delete(iid)
        mark_dirty()

    def var_gen_from_options() -> None:
        """Wypelnia tabele wariantow wszystkimi kombinacjami z opcji."""
        opts: list[list[str]] = []
        opt_names: list[str] = []
        for iid in opt_tree.get_children():
            vals = opt_tree.item(iid, "values")
            name = str(vals[0]).strip()
            if not name:
                continue
            raw = str(vals[1])
            values = [v.strip() for v in raw.split(",") if v.strip()]
            if not values:
                continue
            opts.append(values)
            opt_names.append(name)
        if not opts:
            messagebox.showwarning(
                "Brak opcji",
                "Dodaj najpierw opcje z wartosciami.",
                parent=dlg,
            )
            return
        if len(opts) > 3:
            messagebox.showwarning(
                "Za duzo opcji",
                "Shopify wspiera maksymalnie 3 opcje na produkt.",
                parent=dlg,
            )
            return
        if var_tree.get_children():
            if not messagebox.askyesno(
                "Zastapic warianty?",
                "Tabela wariantow nie jest pusta. Zastapic wszystkie?",
                parent=dlg,
            ):
                return
        for iid in var_tree.get_children():
            var_tree.delete(iid)

        # Cartesian product
        import itertools
        for combo in itertools.product(*opts):
            row_vals: list[str] = []
            for i in range(3):
                row_vals.append(str(combo[i]) if i < len(combo) else "")
            row_vals.extend(["0.00", "", "", "", "deny"])
            var_tree.insert("", "end", values=tuple(row_vals))
        mark_dirty()

    # -------- Zapis --------
    def save_all() -> None:
        collect_editor_into_state()
        variant_templates.save_templates(state["templates"])
        state["templates"] = variant_templates.load_templates()  # re-load (dla is_default adjustment)
        state["dirty"] = False
        refresh_left_list(select_id=state.get("selected_id"))
        show_toast(dlg, "Zapisano szablony")

    # -------- Podpinanie przyciskow --------
    # Lewa kolumna
    left_btns.nametowidget("new_empty").configure(command=new_empty_template)
    left_btns.nametowidget("new_from_shopify").configure(command=new_from_shopify_template)
    left_btns.nametowidget("duplicate").configure(command=duplicate_template)
    left_btns.nametowidget("delete").configure(command=delete_template)
    left_btns.nametowidget("set_default").configure(command=set_default_template)
    # Opcje
    opt_btns.nametowidget("opt_add").configure(command=opt_add)
    opt_btns.nametowidget("opt_edit").configure(command=opt_edit)
    opt_btns.nametowidget("opt_del").configure(command=opt_del)
    # Warianty
    var_btns.nametowidget("var_add").configure(command=var_add)
    var_btns.nametowidget("var_edit").configure(command=var_edit)
    var_btns.nametowidget("var_del").configure(command=var_del)
    var_btns.nametowidget("var_gen").configure(command=var_gen_from_options)
    # Dol
    bottom.nametowidget("save_btn").configure(command=save_all)
    bottom.nametowidget("refresh_btn").configure(command=refresh_from_shopify)

    # Trigger modyfikacji w opt_tree / var_tree - nie ma auto eventu, ale
    # manipulacja zawsze idzie przez ich przyciski (ktore wolaja mark_dirty).

    # -------- Start --------
    refresh_left_list()

    dlg.bind("<Escape>", lambda _e: dlg.destroy())
    return dlg
