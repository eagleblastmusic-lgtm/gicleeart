"""Hub Finanse — jeden ekran: limit DNR, VAT 240k, checklist, compliance."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from datetime import date
from tkinter import messagebox, ttk

from Komponenty._shared.compliance_ui import level_color
from Komponenty._shared.finance_navigation import checklist_nav_target, set_nav
from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast

from .hub_service import load_finance_hub

_BG = "#f4f6f9"
_LEVEL_BG = {
    "ok": "#e8f5e9",
    "caution": "#fff8e1",
    "warn": "#fff3e0",
    "over": "#ffebee",
    "obligation": "#f3e5f5",
}


def build_view(
    parent: tk.Widget,
    on_back: Callable[[], None],
    on_open_component: Callable[[str], None] | None = None,
) -> tk.Widget:
    root = tk.Frame(parent, bg=_BG)
    root.pack(fill="both", expand=True)

    header = tk.Frame(root, bg=_BG, padx=12, pady=8)
    header.pack(fill="x")
    tk.Button(header, text="← Wróć", command=on_back, bg="#fff").pack(side="left")
    tk.Label(header, text="Księgowość — panel", font=("Segoe UI", 14, "bold"), bg=_BG).pack(side="left", padx=12)

    shortcuts = tk.Frame(header, bg=_BG)
    shortcuts.pack(side="right")
    for label, folder, screen in (
        ("Dokumenty", "dokumentysprzedazy", ""),
        ("KPiR", "kpir", ""),
        ("DNR", "dnr", ""),
        ("⚙ Ustawienia księgowości", "kpir", "settings"),
    ):
        ttk.Button(
            shortcuts,
            text=label,
            command=lambda f=folder, s=screen: _open(f, on_open_component, s),
        ).pack(side="left", padx=3)

    top = tk.Frame(root, bg=_BG, padx=12, pady=4)
    top.pack(fill="x")
    y_var = tk.IntVar(value=date.today().year)
    m_var = tk.IntVar(value=date.today().month)
    ttk.Label(top, text="Rok:").pack(side="left")
    ttk.Spinbox(top, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
    ttk.Label(top, text="Miesiąc:").pack(side="left", padx=(8, 0))
    ttk.Spinbox(top, from_=1, to=12, textvariable=m_var, width=4).pack(side="left", padx=4)

    btns = tk.Frame(root, bg=_BG, padx=12, pady=8)
    btns.pack(side="bottom", fill="x")

    body = tk.Frame(root, bg=_BG)
    body.pack(fill="both", expand=True)
    canvas = tk.Canvas(body, highlightthickness=0, bg=_BG)
    vsb = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=_BG, padx=12, pady=4)
    win = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def _on_cfg(_e: tk.Event | None = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        cw = max(canvas.winfo_width(), 760)
        canvas.itemconfigure(win, width=cw)
        wrap = max(520, cw - 48)
        dnr_msg.configure(wraplength=wrap)
        vat_msg.configure(wraplength=wrap)
        mig_lbl.configure(wraplength=wrap)
        pay_lbl.configure(wraplength=wrap)
        for w in comp_inner.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(wraplength=wrap)

    inner.bind("<Configure>", _on_cfg)
    canvas.bind("<Configure>", _on_cfg)
    bind_mousewheel_to_canvas(canvas, inner)

    dnr_box = tk.LabelFrame(inner, text=" Limit kwartalny DNR ", bg=_BG, padx=10, pady=8)
    dnr_box.pack(fill="x", pady=(0, 8))
    dnr_msg = tk.Label(dnr_box, text="—", bg="#fff", wraplength=680, justify="left", font=("Segoe UI", 9, "bold"))
    dnr_msg.pack(fill="x", pady=2)
    dnr_bar = ttk.Progressbar(dnr_box, maximum=100)
    dnr_bar.pack(fill="x", pady=4)

    vat_box = tk.LabelFrame(inner, text=" Zwolnienie VAT (240 000 zł) ", bg=_BG, padx=10, pady=8)
    vat_box.pack(fill="x", pady=(0, 8))
    vat_msg = tk.Label(vat_box, text="—", bg="#fff", wraplength=680, justify="left", font=("Segoe UI", 9, "bold"))
    vat_msg.pack(fill="x", pady=2)
    vat_bar = ttk.Progressbar(vat_box, maximum=100)
    vat_bar.pack(fill="x", pady=4)

    flow_var = tk.StringVar(value="")
    tk.Label(
        inner,
        textvariable=flow_var,
        bg="#e3f2fd",
        fg="#0d47a1",
        font=("Segoe UI", 9),
        wraplength=700,
        justify="left",
        padx=8,
        pady=6,
    ).pack(fill="x", pady=(0, 8))

    pay_var = tk.StringVar(value="")
    pay_box = tk.LabelFrame(inner, text=" Wpłaty w tym miesiącu (JDG) ", bg=_BG, padx=10, pady=8)
    pay_lbl = tk.Label(pay_box, textvariable=pay_var, bg="#e8eaf6", fg="#283593", wraplength=680, justify="left", font=("Segoe UI", 9, "bold"), padx=8, pady=6)
    pay_lbl.pack(fill="x")

    mig_var = tk.StringVar(value="")
    mig_lbl = tk.Label(inner, textvariable=mig_var, bg="#fff3e0", fg="#e65100", wraplength=700, justify="left", padx=8, pady=6)
    mig_lbl.pack(fill="x", pady=(0, 8))

    comp_box = tk.LabelFrame(inner, text=" Compliance ", bg=_BG, padx=10, pady=8)
    comp_box.pack(fill="x", pady=(0, 8))
    comp_inner = tk.Frame(comp_box, bg=_BG)
    comp_inner.pack(fill="x")

    cl_box = tk.LabelFrame(inner, text=" Checklist miesiąca (kliknij → Otwórz) ", bg=_BG, padx=10, pady=8)
    cl_box.pack(fill="x", pady=(0, 4))
    cl_summary = tk.StringVar(value="")
    tk.Label(cl_box, textvariable=cl_summary, bg=_BG, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
    cl_frame = ttk.Frame(cl_box)
    cl_frame.pack(fill="x")
    cl_tree = ttk.Treeview(cl_frame, columns=("sev", "cat", "msg"), show="headings", height=8)
    for cid, txt, w in [("sev", "!", 28), ("cat", "Typ", 72), ("msg", "Opis", 560)]:
        cl_tree.heading(cid, text=txt)
        cl_tree.column(cid, width=w)
    cl_vsb = ttk.Scrollbar(cl_frame, orient="vertical", command=cl_tree.yview)
    cl_tree.configure(yscrollcommand=cl_vsb.set)
    cl_tree.pack(side="left", fill="x", expand=True)
    cl_vsb.pack(side="right", fill="y")
    cl_refs: dict[str, tuple[str, str]] = {}

    def refresh() -> None:
        hub = load_finance_hub(year=y_var.get(), month=m_var.get())
        dnr_lvl = hub.dnr_limit_level
        dnr_msg.configure(
            text=hub.dnr_limit_message or "Brak danych DNR.",
            bg=_LEVEL_BG.get(dnr_lvl, "#fff"),
            fg=level_color(dnr_lvl),
        )
        dnr_bar["value"] = min(100.0, hub.dnr_quarter_pct)
        vat_lvl = hub.vat_level
        vat_msg.configure(
            text=hub.vat_message or "Brak danych VAT.",
            bg=_LEVEL_BG.get(vat_lvl, "#fff"),
            fg=level_color(vat_lvl),
        )
        vat_bar["value"] = min(100.0, hub.vat_pct)
        flow = hub.sales_flow
        flow_var.set(
            "Przepływ: "
            f"bez dokumentu {flow.get('paid_without_invoice', 0)} · "
            f"szkice {flow.get('paid_draft_pending', 0)} · "
            f"do DNR {flow.get('issued_without_dnr', 0)}"
        )
        if hub.payment_active:
            pay_var.set(hub.payment_message)
            pay_box.pack(fill="x", pady=(0, 8))
        elif hub.payment_message:
            pay_var.set(hub.payment_message)
            pay_box.pack(fill="x", pady=(0, 8))
        else:
            pay_var.set("")
            pay_box.pack_forget()
        if hub.migration_alert:
            mig_var.set(hub.migration_alert + (" · Możesz cofnąć błędne przekroczenie w DNR → Kreator migracji." if hub.can_revert_exceed else ""))
            mig_lbl.pack(fill="x", pady=(0, 8))
        else:
            mig_var.set("")
            mig_lbl.pack_forget()
        for w in comp_inner.winfo_children():
            w.destroy()
        for row in hub.compliance:
            tk.Label(
                comp_inner,
                text=f"{row['title']}: {row['message']}",
                fg=level_color(str(row.get("level") or "ok")),
                bg=_BG,
                wraplength=680,
                justify="left",
                font=("Segoe UI", 8),
            ).pack(anchor="w", pady=1)
        cl_refs.clear()
        for i in cl_tree.get_children():
            cl_tree.delete(i)
        for idx, item in enumerate(hub.checklist_items):
            iid = f"cl-{idx}"
            icon = {"error": "✗", "warning": "!", "info": "i"}.get(item.severity, "•")
            cl_tree.insert("", "end", iid=iid, values=(icon, item.category, item.message))
            cl_refs[iid] = (item.category, item.ref)
        cl_summary.set(
            f"Błędy: {hub.checklist_blocking} · Ostrzeżenia: {hub.checklist_warnings} · "
            f"Pokazano {len(hub.checklist_items)} pozycji"
        )
        root.after_idle(_on_cfg)

    def open_checklist_item() -> None:
        sel = cl_tree.selection()
        if not sel:
            return
        cat, ref = cl_refs.get(sel[0], ("", ""))
        target = checklist_nav_target(cat, ref)
        if not target:
            messagebox.showinfo("Księgowość", "Brak bezpośredniego linku dla tej pozycji.", parent=root)
            return
        set_nav(target.module, target.screen, target.ref)
        _open(target.module, on_open_component)

    ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=(0, 6))
    ttk.Button(btns, text="Otwórz pozycję", command=open_checklist_item).pack(side="left", padx=6)

    def _close_month() -> None:
        try:
            from Komponenty.kpir.storage import load_settings

            mode = load_settings().accounting_mode
        except Exception:
            mode = "dnr"
        if mode == "dnr":
            set_nav("dnr", "month_close", "")
            _open("dnr", on_open_component)
        else:
            _open("kpir", on_open_component, "finance_close")

    ttk.Button(btns, text="Zamknięcie miesiąca", command=_close_month).pack(side="left", padx=6)

    cl_tree.bind("<Double-1>", lambda _e: open_checklist_item())
    refresh()
    return root


def _open(
    folder: str,
    on_open_component: Callable[[str], None] | None,
    screen: str = "",
    ref: str = "",
) -> None:
    if screen:
        set_nav(folder, screen, ref)
    if on_open_component:
        on_open_component(folder)
    else:
        messagebox.showinfo("Księgowość", f"Otwórz moduł: {folder}")
