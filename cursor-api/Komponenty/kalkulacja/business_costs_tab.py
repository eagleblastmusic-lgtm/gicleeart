"""Zakładka Koszty działalności — UI i zapis ustawień."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas

from .business_costs import (
    TAX_FORMS,
    ZUS_STAGES,
    compute_business_costs,
    load_business_costs,
    normalize_business_costs,
)
from .calculator import fmt_money, monthly_full_cost_forecast, monthly_revenue_forecast, resolved_sales_mix
from .store import load_settings, save_settings


def build_business_costs_tab(
    parent: ttk.Frame,
    *,
    on_change: Callable[[], None],
) -> dict[str, object]:
    """Buduje zakładkę; zwraca słownik ze stanem i refresh()."""
    state: dict[str, bool] = {"syncing": False}

    inner, canvas = _scrollable(parent)

    def _refresh_scroll() -> None:
        inner.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    top = ttk.Frame(inner)
    top.pack(fill="x", pady=(0, 10))
    ttk.Label(top, text="Uwzględniaj koszty działalności w kalkulacji", font=("Segoe UI", 10, "bold")).pack(
        side="left"
    )
    enabled_var = tk.DoubleVar(value=0.0)
    enabled_lbl = tk.StringVar(value="Wył.")
    scale_row = ttk.Frame(top)
    scale_row.pack(side="right")
    ttk.Label(scale_row, textvariable=enabled_lbl, width=5, anchor="e").pack(side="left", padx=(0, 8))
    enabled_scale = ttk.Scale(scale_row, from_=0, to=1, orient="horizontal", variable=enabled_var, length=140)
    enabled_scale.pack(side="left")

    ttk.Label(
        inner,
        text=(
            "Orientacyjne koszty JDG wg przepisów 2026: ulga na start (6 mies. bez składek społecznych), "
            "potem preferencyjny ZUS (24 mies.) i pełny ZUS. Składka zdrowotna obowiązuje od pierwszego miesiąca."
        ),
        wraplength=760,
        foreground="#555",
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(0, 10))

    form = ttk.LabelFrame(inner, text=" ZUS i opodatkowanie ", padding=10)
    form.pack(fill="x", pady=(0, 10))

    zus_stage_var = tk.StringVar()
    tax_form_var = tk.StringVar()
    relief_month_var = tk.IntVar(value=1)
    sickness_var = tk.BooleanVar(value=False)
    ryczalt_rate_var = tk.StringVar(value="8,5")
    tax_free_var = tk.StringVar(value="30000")

    ttk.Label(form, text="Etap ZUS:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    zus_combo = ttk.Combobox(
        form,
        textvariable=zus_stage_var,
        values=[label for _, label in ZUS_STAGES],
        state="readonly",
        width=48,
    )
    zus_combo.grid(row=0, column=1, sticky="ew", pady=4)

    ttk.Label(form, text="Miesiąc ulgi na start:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
    relief_row = ttk.Frame(form)
    relief_row.grid(row=1, column=1, sticky="w", pady=4)
    relief_lbl = tk.StringVar(value="1 / 6")
    relief_scale = ttk.Scale(
        relief_row,
        from_=1,
        to=6,
        orient="horizontal",
        variable=relief_month_var,
        length=180,
    )
    relief_scale.pack(side="left")
    ttk.Label(relief_row, textvariable=relief_lbl, width=8).pack(side="left", padx=(8, 0))

    ttk.Label(form, text="Forma opodatkowania:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
    tax_combo = ttk.Combobox(
        form,
        textvariable=tax_form_var,
        values=[label for _, label in TAX_FORMS],
        state="readonly",
        width=48,
    )
    tax_combo.grid(row=2, column=1, sticky="ew", pady=4)

    sickness_cb = ttk.Checkbutton(
        form,
        text="Dobrowolna składka chorobowa (nie dotyczy ulgi na start)",
        variable=sickness_var,
    )
    sickness_cb.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 2))

    ryczalt_row = ttk.Frame(form)
    ryczalt_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(2, 0))
    ttk.Label(ryczalt_row, text="Stawka ryczałtu (%):").pack(side="left")
    ryczalt_entry = ttk.Entry(ryczalt_row, textvariable=ryczalt_rate_var, width=8)
    ryczalt_entry.pack(side="left", padx=(6, 0))

    tax_free_row = ttk.Frame(form)
    tax_free_row.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))
    ttk.Label(tax_free_row, text="Kwota wolna od podatku (rocznie, zł):").pack(side="left")
    tax_free_entry = ttk.Entry(tax_free_row, textvariable=tax_free_var, width=10)
    tax_free_entry.pack(side="left", padx=(6, 0))
    ttk.Label(
        tax_free_row,
        text="— tylko skala podatkowa (domyślnie 30 000 zł w 2026)",
        foreground="#666",
        font=("Segoe UI", 8),
    ).pack(side="left", padx=(8, 0))

    form.columnconfigure(1, weight=1)

    zus_hint = tk.StringVar(value="")
    tax_hint = tk.StringVar(value="")
    ttk.Label(form, textvariable=zus_hint, foreground="#666", wraplength=700, font=("Segoe UI", 8)).grid(
        row=6, column=0, columnspan=2, sticky="w", pady=(8, 0)
    )
    ttk.Label(form, textvariable=tax_hint, foreground="#666", wraplength=700, font=("Segoe UI", 8)).grid(
        row=7, column=0, columnspan=2, sticky="w", pady=(4, 0)
    )

    extra = ttk.LabelFrame(inner, text=" Pozostałe koszty miesięczne ", padding=10)
    extra.pack(fill="x", pady=(0, 10))

    accounting_var = tk.StringVar()
    insurance_var = tk.StringVar()
    bank_var = tk.StringVar()
    other_var = tk.StringVar()
    for row_i, (label, var) in enumerate(
        (
            ("Księgowość / biuro rachunkowe:", accounting_var),
            ("Ubezpieczenie OC działalności:", insurance_var),
            ("Bank, terminal, opłaty:", bank_var),
            ("Inne (np. hosting, oprogramowanie):", other_var),
        )
    ):
        ttk.Label(extra, text=label).grid(row=row_i, column=0, sticky="w", padx=(0, 8), pady=4)
        entry = ttk.Entry(extra, textvariable=var, width=14)
        entry.grid(row=row_i, column=1, sticky="w", pady=4)
        entry.bind("<FocusOut>", lambda _e: _persist())
        entry.bind("<Return>", lambda _e: _persist())

    summary = ttk.LabelFrame(inner, text=" Podsumowanie (zysk mixu z wysyłką w koszcie) ", padding=10)
    summary.pack(fill="x")

    summary_rows: dict[str, tk.StringVar] = {}
    labels = (
        ("social", "ZUS społeczny:"),
        ("health", "Składka zdrowotna:"),
        ("pit", "Podatek dochodowy (szac.):"),
        ("fixed", "Pozostałe koszty:"),
        ("total", "Razem koszty działalności:"),
        ("net", "Zysk netto po kosztach:"),
    )
    for row_i, (key, label) in enumerate(labels):
        var = tk.StringVar(value="—")
        summary_rows[key] = var
        font = ("Segoe UI", 10, "bold") if key in ("total", "net") else ("Segoe UI", 10)
        ttk.Label(summary, text=label).grid(row=row_i, column=0, sticky="w", padx=(0, 8), pady=3)
        lbl = ttk.Label(summary, textvariable=var, font=font)
        if key == "net":
            lbl.configure(foreground="#1565c0")
        lbl.grid(row=row_i, column=1, sticky="w", pady=3)

    ttk.Label(
        inner,
        text=(
            "Uwaga: wartości orientacyjne na 2026 r. Na skali uwzględniona kwota wolna 30 000 zł/rok "
            "(lub wartość z pola powyżej). Nie uwzględniają składek ZUS zmniejszających PIT, VAT "
            "ani indywidualnych ulg. Zweryfikuj deklaracje ZUS DRA i PIT przed decyzjami."
        ),
        wraplength=760,
        foreground="#888",
        font=("Segoe UI", 8),
    ).pack(anchor="w", pady=(10, 0))

    def _parse_amount(raw: str) -> float:
        text = raw.strip().replace(" ", "").replace(",", ".")
        if not text:
            return 0.0
        try:
            return max(0.0, float(text))
        except ValueError:
            return 0.0

    def _stage_key_from_label(label: str) -> str:
        for key, text in ZUS_STAGES:
            if text == label:
                return key
        return "ulga_na_start"

    def _tax_key_from_label(label: str) -> str:
        for key, text in TAX_FORMS:
            if text == label:
                return key
        return "skala"

    def _label_from_key(mapping: tuple[tuple[str, str], ...], key: str) -> str:
        for k, text in mapping:
            if k == key:
                return text
        return mapping[0][1]

    def _collect_config() -> dict[str, object]:
        return normalize_business_costs(
            {
                "enabled": enabled_var.get() >= 0.5,
                "zus_stage": _stage_key_from_label(zus_stage_var.get()),
                "tax_form": _tax_key_from_label(tax_form_var.get()),
                "relief_month": int(relief_month_var.get()),
                "voluntary_sickness": sickness_var.get(),
                "ryczalt_rate_pct": _parse_amount(ryczalt_rate_var.get()),
                "accounting_monthly": _parse_amount(accounting_var.get()),
                "insurance_oc_monthly": _parse_amount(insurance_var.get()),
                "bank_fees_monthly": _parse_amount(bank_var.get()),
                "other_monthly": _parse_amount(other_var.get()),
                "tax_free_annual": _parse_amount(tax_free_var.get()),
            }
        )

    def _update_tax_hint() -> None:
        tax = _tax_key_from_label(tax_form_var.get())
        if tax == "skala":
            free = _parse_amount(tax_free_var.get())
            if free <= 0:
                free = 30_000.0
            tax_free_entry.configure(state="normal")
            tax_hint.set(
                f"Skala: PIT od zysku brutto (przychód − koszt prod. z wysyłką), rocznie — 12% do 120 000 zł "
                f"(po kwocie wolnej {fmt_money(free)}/rok), 32% od nadwyżki. Pozostałe koszty JDG osobno."
            )
        elif tax == "liniowy":
            tax_free_entry.configure(state="disabled")
            tax_hint.set(
                "Podatek liniowy: 19% od zysku brutto miesięcznego — bez kwoty wolnej. Pozostałe koszty JDG osobno."
            )
        else:
            tax_free_entry.configure(state="disabled")
            tax_hint.set("Ryczałt: stawka % od przychodu brutto — bez kwoty wolnej i bez odliczenia KUP.")
        _refresh_scroll()

    def _update_zus_hint() -> None:
        stage = _stage_key_from_label(zus_stage_var.get())
        month = int(relief_month_var.get())
        relief_lbl.set(f"{month} / 6")
        if stage == "ulga_na_start":
            zus_hint.set(
                f"Ulga na start — miesiąc {month} z 6. Brak składek społecznych (emerytalna, rentowa, "
                f"wypadkowa, FP). Obowiązkowa tylko składka zdrowotna. Po 6 miesiącach: preferencyjny ZUS (24 mies.)."
            )
            sickness_cb.configure(state="disabled")
            sickness_var.set(False)
            relief_scale.configure(state="normal")
        elif stage == "preferencyjny":
            zus_hint.set(
                "Preferencyjny ZUS — podstawa 1 441,80 zł (30% minimalnego wynagrodzenia). "
                "Dostępny przez 24 miesiące po zakończeniu ulgi na start."
            )
            sickness_cb.configure(state="normal")
            relief_scale.configure(state="disabled")
        else:
            zus_hint.set(
                "Pełny ZUS — podstawa 5 652,00 zł (60% prognozowanego przeciętnego wynagrodzenia)."
            )
            sickness_cb.configure(state="normal")
            relief_scale.configure(state="disabled")
        _update_tax_hint()

    def refresh_tab() -> None:
        cfg = _collect_config()
        mix = resolved_sales_mix()
        monthly_revenue = monthly_revenue_forecast(mix)
        monthly_production_cost = monthly_full_cost_forecast(mix)
        result = compute_business_costs(
            cfg,
            monthly_revenue=monthly_revenue,
            monthly_production_cost=monthly_production_cost,
        )
        if not cfg["enabled"]:
            for var in summary_rows.values():
                var.set("—")
            summary_rows["total"].set("wyłączone")
            summary_rows["net"].set("—")
            return
        summary_rows["social"].set(fmt_money(result["social_insurance"]))
        summary_rows["health"].set(fmt_money(result["health_insurance"]))
        summary_rows["pit"].set(fmt_money(result["pit"]))
        summary_rows["fixed"].set(fmt_money(result["fixed_costs"]))
        summary_rows["total"].set(f"{fmt_money(result['total'])} / {fmt_money(result['daily_total'])}")
        summary_rows["net"].set(f"{fmt_money(result['net_profit'])} / {fmt_money(result['daily_net'])}")

    def _persist() -> None:
        if state["syncing"]:
            return
        settings = load_settings()
        settings["business_costs"] = _collect_config()
        save_settings(settings)
        refresh_tab()
        on_change()

    def _on_enabled_release(_evt: object = None) -> None:
        val = 1.0 if enabled_var.get() >= 0.5 else 0.0
        enabled_var.set(val)
        enabled_lbl.set("Wł." if val >= 0.5 else "Wył.")
        _persist()

    def _load_from_settings() -> None:
        state["syncing"] = True
        cfg = load_business_costs()
        enabled_var.set(1.0 if cfg["enabled"] else 0.0)
        enabled_lbl.set("Wł." if cfg["enabled"] else "Wył.")
        zus_stage_var.set(_label_from_key(ZUS_STAGES, str(cfg["zus_stage"])))
        tax_form_var.set(_label_from_key(TAX_FORMS, str(cfg["tax_form"])))
        relief_month_var.set(int(cfg["relief_month"]))
        sickness_var.set(bool(cfg["voluntary_sickness"]))
        ryczalt_rate_var.set(f"{float(cfg['ryczalt_rate_pct']):g}".replace(".", ","))
        accounting_var.set(f"{float(cfg['accounting_monthly']):.2f}".replace(".", ","))
        insurance_var.set(f"{float(cfg['insurance_oc_monthly']):.2f}".replace(".", ","))
        bank_var.set(f"{float(cfg['bank_fees_monthly']):.2f}".replace(".", ","))
        other_var.set(f"{float(cfg['other_monthly']):.2f}".replace(".", ","))
        tax_free_var.set(f"{float(cfg.get('tax_free_annual', 30_000)):.0f}")
        state["syncing"] = False
        _update_zus_hint()

    enabled_scale.bind("<ButtonRelease-1>", _on_enabled_release)
    relief_scale.configure(command=lambda _v: (_update_zus_hint(), _persist()))
    zus_combo.bind("<<ComboboxSelected>>", lambda _e: (_update_zus_hint(), _persist()))
    tax_combo.bind("<<ComboboxSelected>>", lambda _e: (_update_tax_hint(), _persist()))
    sickness_cb.configure(command=_persist)
    ryczalt_entry.bind("<FocusOut>", lambda _e: _persist())
    ryczalt_entry.bind("<Return>", lambda _e: _persist())
    tax_free_entry.bind("<FocusOut>", lambda _e: (_update_tax_hint(), _persist()))
    tax_free_entry.bind("<Return>", lambda _e: (_update_tax_hint(), _persist()))

    _load_from_settings()
    refresh_tab()
    _refresh_scroll()

    return {"refresh": refresh_tab}


def _scrollable(parent: tk.Misc) -> tuple[ttk.Frame, tk.Canvas]:
    wrap = ttk.Frame(parent)
    wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(wrap, highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _scrollregion(_evt: object = None) -> None:
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    inner.bind("<Configure>", _scrollregion)

    def _fill_width(evt: tk.Event) -> None:
        canvas.itemconfigure(win_id, width=evt.width)

    canvas.bind("<Configure>", _fill_width)

    def _focus_canvas(_evt: object = None) -> None:
        try:
            canvas.focus_set()
        except tk.TclError:
            pass

    wrap.bind("<Enter>", _focus_canvas)
    canvas.bind("<Enter>", _focus_canvas)

    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    bind_mousewheel_to_canvas(canvas, inner)
    return inner, canvas
