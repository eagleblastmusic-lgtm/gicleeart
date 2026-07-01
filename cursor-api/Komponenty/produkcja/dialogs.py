"""Pomocnicze dialogi dla Produkcji: edytor szablonow paczek i widok 'Dzis do zrobienia'."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk
from typing import Callable

from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center
from Komponenty.produkcja import package_templates
from Komponenty.produkcja.frame_variant import shipping_lookup_key


# ---------------------------------------------------------------------------
# Szablony paczek — edytor
# ---------------------------------------------------------------------------

def open_package_templates_editor(parent: tk.Misc) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Szablony paczek — wymiary / waga")
    position_toplevel_screen_center(dlg, 760, 520)
    dlg.minsize(680, 420)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    head = ttk.Frame(dlg, padding=(12, 10))
    head.pack(fill="x")
    ttk.Label(
        head,
        text="📏 Szablony paczek",
        font=("Segoe UI", 13, "bold"),
    ).pack(side="left")
    ttk.Label(
        head,
        text="  Klucz to {DREWNO} {ROZMIAR}, np. \"DAB M\", \"SOSNA XL\".",
        foreground="#666",
    ).pack(side="left", padx=(10, 0))

    body = ttk.Frame(dlg, padding=(12, 4))
    body.pack(fill="both", expand=True)

    cols = ("key", "length_cm", "width_cm", "height_cm", "weight_kg", "updated_at")
    tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="browse", height=10)
    tree.heading("key", text="Klucz")
    tree.heading("length_cm", text="Dl. [cm]")
    tree.heading("width_cm", text="Szer. [cm]")
    tree.heading("height_cm", text="Wys. [cm]")
    tree.heading("weight_kg", text="Waga [kg]")
    tree.heading("updated_at", text="Zmieniono")
    tree.column("key", width=130, anchor="w")
    tree.column("length_cm", width=80, anchor="e")
    tree.column("width_cm", width=80, anchor="e")
    tree.column("height_cm", width=80, anchor="e")
    tree.column("weight_kg", width=80, anchor="e")
    tree.column("updated_at", width=150, anchor="w")
    vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    form = ttk.LabelFrame(dlg, text="Dodaj / edytuj", padding=10)
    form.pack(fill="x", padx=12, pady=(6, 8))
    for c in range(6):
        form.columnconfigure(c, weight=1 if c in (1, 3, 5) else 0)

    key_var = tk.StringVar()
    len_var = tk.StringVar()
    wid_var = tk.StringVar()
    hei_var = tk.StringVar()
    wei_var = tk.StringVar()

    ttk.Label(form, text="Klucz:").grid(row=0, column=0, sticky="w", padx=(0, 4))
    ttk.Entry(form, textvariable=key_var, width=16).grid(row=0, column=1, sticky="w", padx=(0, 10))
    ttk.Label(form, text="Dl [cm]:").grid(row=0, column=2, sticky="w", padx=(0, 4))
    ttk.Entry(form, textvariable=len_var, width=10).grid(row=0, column=3, sticky="w", padx=(0, 10))
    ttk.Label(form, text="Szer [cm]:").grid(row=0, column=4, sticky="w", padx=(0, 4))
    ttk.Entry(form, textvariable=wid_var, width=10).grid(row=0, column=5, sticky="w")

    ttk.Label(form, text="Wys [cm]:").grid(row=1, column=0, sticky="w", padx=(0, 4), pady=(6, 0))
    ttk.Entry(form, textvariable=hei_var, width=10).grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(6, 0))
    ttk.Label(form, text="Waga [kg]:").grid(row=1, column=2, sticky="w", padx=(0, 4), pady=(6, 0))
    ttk.Entry(form, textvariable=wei_var, width=10).grid(row=1, column=3, sticky="w", padx=(0, 10), pady=(6, 0))

    def _refresh() -> None:
        for iid in tree.get_children():
            tree.delete(iid)
        for t in package_templates.load_templates():
            tree.insert(
                "", "end", iid=t.key,
                values=(
                    t.key,
                    f"{t.length_cm:g}",
                    f"{t.width_cm:g}",
                    f"{t.height_cm:g}",
                    f"{t.weight_kg:g}",
                    t.updated_at.replace("T", " ")[:16],
                ),
            )

    def _on_row_selected(_e: tk.Event | None = None) -> None:
        sel = tree.selection()
        if not sel:
            return
        t = package_templates.get_template(sel[0])
        if not t:
            return
        key_var.set(t.key)
        len_var.set(f"{t.length_cm:g}")
        wid_var.set(f"{t.width_cm:g}")
        hei_var.set(f"{t.height_cm:g}")
        wei_var.set(f"{t.weight_kg:g}")

    tree.bind("<<TreeviewSelect>>", _on_row_selected)

    def _parse_float(raw: str) -> float:
        try:
            return float((raw or "0").replace(",", "."))
        except ValueError:
            return 0.0

    def _save() -> None:
        k = key_var.get().strip().upper()
        if not k:
            messagebox.showwarning("Brak klucza", "Podaj klucz szablonu, np. 'DAB M'.", parent=dlg)
            return
        try:
            package_templates.upsert_template(
                k,
                length_cm=_parse_float(len_var.get()),
                width_cm=_parse_float(wid_var.get()),
                height_cm=_parse_float(hei_var.get()),
                weight_kg=_parse_float(wei_var.get()),
            )
        except ValueError as e:
            messagebox.showerror("Blad", str(e), parent=dlg)
            return
        show_toast(dlg, f"Zapisano: {k}", duration_ms=1400)
        _refresh()
        if tree.exists(k):
            tree.selection_set(k)
            tree.see(k)

    def _delete() -> None:
        sel = tree.selection()
        if not sel:
            return
        k = sel[0]
        if not messagebox.askyesno("Usunac?", f"Usunac szablon '{k}'?", parent=dlg):
            return
        package_templates.delete_template(k)
        _refresh()
        for v in (key_var, len_var, wid_var, hei_var, wei_var):
            v.set("")

    def _reset() -> None:
        if not messagebox.askyesno(
            "Przywrocic domyslne?",
            "To zastapi biezace szablony zestawem domyslnym. Kontynuowac?",
            parent=dlg,
        ):
            return
        package_templates.reset_to_defaults()
        _refresh()

    btns = ttk.Frame(dlg, padding=(12, 4))
    btns.pack(fill="x", pady=(0, 10))
    ttk.Button(btns, text="💾 Zapisz / aktualizuj", command=_save).pack(side="left")
    ttk.Button(btns, text="🗑 Usun zaznaczony", command=_delete).pack(side="left", padx=6)
    ttk.Button(btns, text="↺ Domyslne", command=_reset).pack(side="left", padx=(20, 0))
    ttk.Button(btns, text="Zamknij", command=dlg.destroy).pack(side="right")

    _refresh()
    dlg.bind("<Escape>", lambda _e: dlg.destroy())


# ---------------------------------------------------------------------------
# Dzis do zrobienia
# ---------------------------------------------------------------------------

# Kazdy "bucket" to etap + predykat, ktory mowi czy zamowienie tam trafia.
# Zamowienie moze trafic do KILKU bucketow naraz (np. czeka na wyciecie ramki
# i jest gotowe do pakowania).

def _bucket_wyciecie(o: dict) -> bool:
    return int(o.get("ramka_step") or 0) < 2 and int(o.get("ramka_step") or 0) >= 1

def _bucket_szlif(o: dict) -> bool:
    return int(o.get("ramka_step") or 0) == 2

def _bucket_malowanie(o: dict) -> bool:
    return int(o.get("ramka_step") or 0) == 3

def _bucket_wydruk(o: dict) -> bool:
    return int(o.get("wydruk_step") or 0) < 2

def _bucket_zlozenie(o: dict, ramka_ready: Callable[[dict], bool], wydruk_ready: Callable[[dict], bool]) -> bool:
    return ramka_ready(o) and wydruk_ready(o) and not o.get("zlozone")

def _bucket_pakowanie(o: dict) -> bool:
    return bool(o.get("zlozone")) and not o.get("spakowane")

def _bucket_nadanie(o: dict) -> bool:
    return bool(o.get("spakowane")) and not o.get("wyslane")


def open_today_board(
    parent: tk.Misc,
    *,
    orders: list[dict],
    ramka_ready: Callable[[dict], bool],
    wydruk_ready: Callable[[dict], bool],
    on_select_order: Callable[[str], None] | None = None,
) -> None:
    """Widok 'Dzis do zrobienia' — grupuje aktywne zamowienia po etapach."""
    dlg = tk.Toplevel(parent)
    dlg.title("Dzis do zrobienia")
    position_toplevel_screen_center(dlg, 960, 680)
    dlg.minsize(780, 520)
    try:
        dlg.transient(parent.winfo_toplevel())
    except (tk.TclError, AttributeError):
        pass

    head = ttk.Frame(dlg, padding=(12, 10))
    head.pack(fill="x")
    ttk.Label(
        head,
        text=f"📋 Dzis do zrobienia — {date.today().isoformat()}",
        font=("Segoe UI", 13, "bold"),
    ).pack(side="left")
    ttk.Label(
        head,
        text="  Grupowane po etapie; jedno zamowienie moze byc w kilku sekcjach",
        foreground="#666",
    ).pack(side="left", padx=(10, 0))

    active = [o for o in orders if not o.get("wyslane")]

    buckets: list[tuple[str, str, Callable[[dict], bool]]] = [
        ("✂ Wyciecie ramek",       "#6a1b9a", _bucket_wyciecie),
        ("🪵 Szlif ramek",          "#4527a0", _bucket_szlif),
        ("🎨 Malowanie ramek",      "#ef6c00", _bucket_malowanie),
        ("🖨 Wydruk",               "#1565c0", _bucket_wydruk),
        (
            "🧩 Zlozenie (komponenty gotowe)",
            "#2e7d32",
            lambda o: _bucket_zlozenie(o, ramka_ready, wydruk_ready),
        ),
        ("📦 Pakowanie",            "#00695c", _bucket_pakowanie),
        ("🚚 Nadanie / wysylka",    "#b71c1c", _bucket_nadanie),
    ]

    canvas = tk.Canvas(dlg, borderwidth=0, highlightthickness=0)
    vsb = ttk.Scrollbar(dlg, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
    vsb.pack(side="right", fill="y", pady=(0, 12))

    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_configure(_e: tk.Event | None = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.itemconfigure(win_id, width=canvas.winfo_width())

    inner.bind("<Configure>", _on_configure)
    canvas.bind("<Configure>", _on_configure)

    def _on_mousewheel(e: tk.Event) -> None:
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _open(oid: str) -> None:
        if on_select_order is not None:
            on_select_order(oid)
            dlg.destroy()

    total_tasks = 0
    for title, color, predicate in buckets:
        matched = [o for o in active if predicate(o)]
        section = ttk.Frame(inner)
        section.pack(fill="x", pady=(10, 2), padx=(0, 10))
        head_row = tk.Frame(section, bg=color)
        head_row.pack(fill="x")
        tk.Label(
            head_row,
            text=f"  {title}  ({len(matched)})",
            bg=color, fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=6, pady=4,
        ).pack(anchor="w")
        if not matched:
            ttk.Label(
                section, text="   — nic w tym etapie",
                foreground="#888", font=("Segoe UI", 9, "italic"),
            ).pack(anchor="w", padx=6, pady=(2, 6))
            continue

        for o in matched:
            total_tasks += 1
            row = ttk.Frame(section)
            row.pack(fill="x", padx=6, pady=1)
            oid = str(o.get("id") or "")
            client = (o.get("client") or "(bez klienta)").strip()
            title_art = (o.get("tytul_obrazu") or "").strip()
            cl_text = client if not title_art else f"{client}  —  {title_art}"
            variant = f"{o.get('ramka_drewno','')} {o.get('ramka_rozmiar','')}"
            days = _age_days(o)
            age = f"  ({days}d)" if days >= 0 else ""

            btn = tk.Label(
                row, text=f"  {oid}  ·  {cl_text}{age}",
                fg="#0d47a1", cursor="hand2",
                font=("Segoe UI", 9, "underline"),
                anchor="w",
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda _e, x=oid: _open(x))

            ttk.Label(
                row, text=f"  [{variant.strip() or '?'}]",
                foreground="#555",
            ).pack(side="left")

    foot = ttk.Frame(dlg, padding=(12, 4))
    foot.pack(fill="x", pady=(0, 8))
    ttk.Label(
        foot,
        text=f"Razem zadan do zrobienia: {total_tasks}   ·   Aktywnych zamowien: {len(active)}",
        foreground="#555",
    ).pack(side="left")
    ttk.Button(foot, text="Zamknij", command=dlg.destroy).pack(side="right")
    dlg.bind("<Escape>", lambda _e: dlg.destroy())


def _age_days(order: dict) -> int:
    raw = str(order.get("data_zamowienia") or "").strip()
    if not raw:
        return -1
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return -1
    return (date.today() - d).days


# Jeden wspolny unused import na wypadek przyszlego uzytku
_ = shipping_lookup_key
