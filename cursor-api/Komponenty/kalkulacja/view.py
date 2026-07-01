"""Widok inline — kalkulator kosztów produkcji ramek."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast

from .calculator import (
    FORMATS,
    SECTION_LABELS,
    WOODS,
    WOOD_ORIGINS,
    compute_variant,
    fmt_hourly,
    fmt_money,
    fmt_pct,
    fmt_production_hours,
    fmt_monthly_full_cost_forecast,
    fmt_monthly_profit_forecast,
    fmt_monthly_revenue_forecast,
    monthly_full_cost_forecast,
    fmt_work_days,
    fmt_work_hours,
    hourly_profit,
    parse_mix_units,
    apply_sales_change,
    apply_sales_growth,
    effective_frames_per_day,
    format_frame_count,
    frames_per_day_from_calculator,
    pricing_snapshot,
    redistribute_mix_total,
    total_mix_units,
    weighted_production_hours_per_frame,
    work_days_from_sales,
    production_minutes_from_hours,
    resolve_production_minutes,
    resolved_sales_mix,
    sell_key,
    monthly_profit_forecast,
    monthly_revenue_forecast,
    monthly_work_hours,
    normalize_manual_frames_per_day,
    normalize_sales_mix,
    wood_cost_for_variant,
)
from .variant_template_sync import sync_variant_template_prices
from .business_costs import compare_tax_forms, fmt_monthly_net_forecast, load_business_costs
from .business_costs_tab import build_business_costs_tab
from .cost_structure import notify_cost_structure_update, open_cost_structure_window
from .import_excel import import_from_xlsm
from .mix_share_dialog import open_mix_share_dialog
from .financial_goal_dialog import open_financial_goal_dialog
from .store import (
    load_cost_lines,
    load_materials,
    load_sales_mix,
    load_settings,
    load_wood_defaults,
    save_cost_lines,
    save_materials,
    save_sales_mix,
    save_settings,
    save_wood_defaults,
)

_ACCENT = "#1565c0"
_SUCCESS = "#2e7d32"

_BREAKDOWN_HEADER_TAGS: dict[str, tuple[str, str, str]] = {
    "production": ("header_production", "#eef4fc", "#4a6fa5"),
    "print": ("header_print", "#f3f0fa", "#6b5b8a"),
    "packaging": ("header_packaging", "#eef8f1", "#4a7c59"),
    "shipping": ("header_shipping", "#fdf6ee", "#9a6b42"),
}

_SUMMARY_CELL_STYLES: dict[str, tuple[str, str, str]] = {
    "full": ("#fff7ed", "#9a6b42", "#c2410c"),
    "price": ("#eef4fc", "#4a6fa5", "#1d4ed8"),
    "profit": ("#ecfdf3", "#3d7a55", "#15803d"),
}


def _scrollable(parent: tk.Misc) -> tuple[ttk.Frame, tk.Canvas]:
    wrap = ttk.Frame(parent)
    wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(wrap, highlightthickness=0, bd=0)
    vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    inner = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _scrollregion(_evt: object = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner.bind("<Configure>", _scrollregion)

    def _fill_width(evt: tk.Event) -> None:
        canvas.itemconfigure(win_id, width=evt.width)

    canvas.bind("<Configure>", _fill_width)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return inner, canvas


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    root = ttk.Frame(parent)
    root.pack(fill="both", expand=True)

    header = ttk.Frame(root, padding=(12, 10, 12, 6))
    header.pack(fill="x")
    ttk.Button(header, text="← Wróć", command=on_back).pack(side="left")
    ttk.Label(header, text="Kalkulator kosztów", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(12, 0))
    ttk.Label(
        header,
        text="Koszty produkcji ramek · marże · drewno",
        foreground="#666",
        font=("Segoe UI", 9),
    ).pack(side="left", padx=(10, 0))
    ttk.Button(header, text="Struktura kosztów", command=lambda: open_cost_structure_window(root)).pack(
        side="right"
    )

    notebook = ttk.Notebook(root, padding=(8, 0, 8, 8))
    notebook.pack(fill="both", expand=True)

    tab_calc = ttk.Frame(notebook, padding=8)
    tab_mix = ttk.Frame(notebook, padding=8)
    tab_wood = ttk.Frame(notebook, padding=8)
    tab_materials = ttk.Frame(notebook, padding=8)
    tab_business = ttk.Frame(notebook, padding=8)
    tab_import = ttk.Frame(notebook, padding=8)
    notebook.add(tab_calc, text="Kalkulator")
    notebook.add(tab_mix, text="Mix sprzedaży")
    notebook.add(tab_wood, text="Drewno")
    notebook.add(tab_materials, text="Materiały")
    notebook.add(tab_business, text="Koszty działalności")
    notebook.add(tab_import, text="Import Excel")

    # --- Kalkulator ---
    calc_top = ttk.Frame(tab_calc)
    calc_top.pack(fill="x", pady=(0, 8))
    wood_var = tk.StringVar(value="SOSNA")
    fmt_var = tk.StringVar(value="A4")
    wood_origin_var = tk.StringVar(value="stolarz24")
    price_var = tk.StringVar(value="")
    markup_var = tk.StringVar(value="")
    margin_var = tk.StringVar(value="")
    pricing_state: dict[str, object] = {"driver": None, "syncing": False, "total_cost": 0.0}

    ttk.Label(calc_top, text="Gatunek:").pack(side="left")
    wood_cb = ttk.Combobox(calc_top, textvariable=wood_var, values=list(WOODS), width=10, state="readonly")
    wood_cb.pack(side="left", padx=(4, 12))
    ttk.Label(calc_top, text="Format:").pack(side="left")
    fmt_cb = ttk.Combobox(calc_top, textvariable=fmt_var, values=list(FORMATS), width=8, state="readonly")
    fmt_cb.pack(side="left", padx=(4, 12))
    ttk.Label(calc_top, text="Pochodzenie drewna:").pack(side="left")
    wood_origin_cb = ttk.Combobox(
        calc_top,
        textvariable=wood_origin_var,
        values=list(WOOD_ORIGINS),
        width=24,
        state="readonly",
    )
    wood_origin_cb.pack(side="left", padx=(4, 12))

    summary_frame = ttk.LabelFrame(tab_calc, text=" Podsumowanie ", padding=10)
    summary_frame.pack(fill="x", pady=(0, 8))
    for c in range(4):
        summary_frame.columnconfigure(c, weight=1)

    cost_lbl = tk.StringVar(value="—")
    full_cost_lbl = tk.StringVar(value="—")
    price_lbl = tk.StringVar(value="—")
    profit_lbl = tk.StringVar(value="—")
    margin_lbl = tk.StringVar(value="—")
    markup_lbl = tk.StringVar(value="—")
    time_var = tk.StringVar(value="0,75")
    hourly_lbl = tk.StringVar(value="—")
    time_state: dict[str, bool] = {"syncing": False}

    def _sum_cell(
        row: int,
        col: int,
        title: str,
        var: tk.StringVar,
        *,
        big: bool = False,
        style: str | None = None,
    ) -> None:
        if style and style in _SUMMARY_CELL_STYLES:
            bg, title_fg, value_fg = _SUMMARY_CELL_STYLES[style]
            box = tk.Frame(summary_frame, bg=bg, padx=8, pady=6)
            box.grid(row=row, column=col, sticky="nsew", padx=4, pady=2)
            tk.Label(box, text=title, bg=bg, fg=title_fg, font=("Segoe UI", 9)).pack(anchor="w")
            value_font = ("Segoe UI", 13, "bold") if big else ("Segoe UI", 11, "bold")
            tk.Label(box, textvariable=var, bg=bg, fg=value_fg, font=value_font).pack(anchor="w")
            return
        box = ttk.Frame(summary_frame)
        box.grid(row=row, column=col, sticky="nsew", padx=6, pady=2)
        ttk.Label(box, text=title, foreground="#555").pack(anchor="w")
        value_font = ("Segoe UI", 13, "bold") if big else ("Segoe UI", 11, "bold")
        ttk.Label(box, textvariable=var, font=value_font).pack(anchor="w")

    _sum_cell(0, 0, "Koszt produkcji", cost_lbl, big=True)
    _sum_cell(0, 1, "Koszt produkcji z wysyłką", full_cost_lbl, style="full")
    _sum_cell(0, 2, "Cena sprzedaży", price_lbl, style="price")
    _sum_cell(0, 3, "Zysk", profit_lbl, style="profit")
    _sum_cell(1, 0, "Marża", margin_lbl)
    _sum_cell(1, 1, "Narzut", markup_lbl)
    _sum_cell(1, 2, "Zarobek na godzinę", hourly_lbl)

    pricing_frame = ttk.LabelFrame(tab_calc, text="Cennik wariantu: SOSNA · A4", padding=10)
    pricing_frame.pack(fill="x", pady=(0, 8))
    for c in range(6):
        pricing_frame.columnconfigure(c, weight=1 if c % 2 == 1 else 0)

    ttk.Label(pricing_frame, text="Narzut (%)").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
    markup_entry = ttk.Entry(pricing_frame, textvariable=markup_var, width=12)
    markup_entry.grid(row=0, column=1, sticky="w", pady=4)

    ttk.Label(pricing_frame, text="Marża (%)").grid(row=0, column=2, sticky="w", padx=(16, 6), pady=4)
    margin_entry = ttk.Entry(pricing_frame, textvariable=margin_var, width=12)
    margin_entry.grid(row=0, column=3, sticky="w", pady=4)

    price_row = ttk.Frame(pricing_frame)
    price_row.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(4, 0))
    price_left = ttk.Frame(price_row)
    price_left.pack(side="left")
    ttk.Label(price_left, text="Cena (edycja):").pack(side="left")
    price_entry = ttk.Entry(price_left, textvariable=price_var, width=14)
    price_entry.pack(side="left", padx=(6, 8))
    save_price_btn = ttk.Button(price_left, text="Zapisz cenę")
    save_price_btn.pack(side="left")
    update_tpl_btn = ttk.Button(price_left, text="Zaktualizuj w szablonie")
    update_tpl_btn.pack(side="left", padx=(8, 0))

    time_right = ttk.Frame(price_row)
    time_right.pack(side="right")
    ttk.Label(time_right, text="Czas produkcji (h):").pack(side="left")
    ttk.Entry(time_right, textvariable=time_var, width=10).pack(side="left", padx=(6, 0))

    ttk.Label(
        pricing_frame,
        text="Cena i czas dotyczą wybranego wariantu. Po zapisie ceny przeliczane są narzut i marża; "
        "zarobek na godzinę zależy od czasu produkcji. "
        "„Zaktualizuj w szablonie” zapisuje ceny wszystkich 6 wariantów (M/L/XL × sosna/dąb) "
        "do variant_templates.json — źródło cen przy dodawaniu produktów w dodajobraz.",
        foreground="#666",
        wraplength=680,
    ).grid(row=2, column=0, columnspan=6, sticky="w", pady=(8, 0))

    breakdown = ttk.Treeview(
        tab_calc,
        columns=("section", "cost"),
        show="headings",
        height=14,
    )
    breakdown.heading("section", text="Pozycja")
    breakdown.heading("cost", text="Koszt")
    breakdown.column("section", width=420, anchor="w")
    breakdown.column("cost", width=100, anchor="e")
    for _tag, bg, fg in _BREAKDOWN_HEADER_TAGS.values():
        breakdown.tag_configure(
            _tag,
            background=bg,
            foreground=fg,
            font=("Segoe UI", 9),
        )
    breakdown.tag_configure(
        "header_other",
        background="#f3f4f6",
        foreground="#6b7280",
        font=("Segoe UI", 9),
    )
    breakdown.pack(fill="both", expand=True)

    section_totals = ttk.Frame(tab_calc)
    section_totals.pack(fill="x", pady=(8, 0))
    sec_prod = tk.StringVar(value="")
    sec_print = tk.StringVar(value="")
    sec_pack = tk.StringVar(value="")
    sec_ship = tk.StringVar(value="")
    for i, (lbl, var) in enumerate(
        [
            ("Produkcja:", sec_prod),
            ("Wydruk:", sec_print),
            ("Opakowanie:", sec_pack),
            ("Wysyłka:", sec_ship),
        ]
    ):
        ttk.Label(section_totals, text=lbl).grid(row=0, column=i * 2, sticky="w", padx=(0, 4))
        ttk.Label(section_totals, textvariable=var, font=("Segoe UI", 9, "bold")).grid(
            row=0, column=i * 2 + 1, sticky="w", padx=(0, 14)
        )

    # --- Mix sprzedaży ---
    mix_hint = ttk.Label(
        tab_mix,
        text="Udział % z „Udział na 100 szt.” jest zapisany i stały. ± zmienia łączną sprzedaż, "
        "sztuki przeliczane wg tego udziału. Dwuklik „Sprzedaż” — zmiana łącznej liczby sztuk.",
        foreground="#666",
        wraplength=680,
    )
    mix_hint.pack(anchor="w", pady=(0, 6))

    mix_total_var = tk.StringVar(value="")
    mix_total_state: dict[str, bool] = {"syncing": False}
    mix_growth_var = tk.StringVar(value="")
    mix_growth_row = ttk.Frame(tab_mix)
    mix_growth_row.pack(fill="x", pady=(0, 6))
    ttk.Button(mix_growth_row, text="Udział na 100 szt.", command=lambda: open_mix_share_dialog(root, on_apply=refresh_mix)).pack(
        side="left", padx=(0, 12)
    )
    ttk.Button(
        mix_growth_row,
        text="Cel finansowy",
        command=lambda: open_financial_goal_dialog(root, on_apply=refresh_mix),
    ).pack(side="left", padx=(0, 12))
    ttk.Label(mix_growth_row, text="Symuluj zmianę sprzedaży:").pack(side="left")
    mix_growth_minus_btn = ttk.Button(mix_growth_row, text="−", width=3)
    mix_growth_minus_btn.pack(side="left", padx=(6, 2))
    mix_growth_entry = ttk.Entry(mix_growth_row, textvariable=mix_growth_var, width=8)
    mix_growth_entry.pack(side="left", padx=(0, 2))
    mix_growth_plus_btn = ttk.Button(mix_growth_row, text="+", width=3)
    mix_growth_plus_btn.pack(side="left", padx=(0, 12))
    ttk.Label(mix_growth_row, text="Sprzedane ramki (razem):").pack(side="left", padx=(0, 4))
    mix_total_entry = ttk.Entry(mix_growth_row, textvariable=mix_total_var, width=8)
    mix_total_entry.pack(side="left")
    mix_total_btn = ttk.Button(mix_growth_row, text="Ustaw", width=7)
    mix_total_btn.pack(side="left", padx=(6, 0))
    ttk.Label(
        mix_growth_row,
        text="Wpisz liczbę sztuk, potem + lub − (wg udziału); Enter — dodaje wpisaną liczbę.",
        foreground="#666",
    ).pack(side="left", padx=(0, 0))

    mix_tree = ttk.Treeview(
        tab_mix,
        columns=("wood", "format", "price", "cost", "profit", "weight", "units"),
        show="headings",
        height=8,
    )
    for col, title, w in [
        ("wood", "Gatunek", 70),
        ("format", "Format", 60),
        ("price", "Cena", 90),
        ("cost", "Koszt produkcji z wysyłką", 150),
        ("profit", "Zysk", 90),
        ("weight", "Udział", 70),
        ("units", "Sprzedaż", 90),
    ]:
        mix_tree.heading(col, text=title)
        mix_tree.column(col, width=w, anchor="center" if col in ("wood", "format", "weight") else "e")
    mix_tree.pack(fill="both", expand=True, pady=(0, 8))

    mix_summary_row = ttk.Frame(tab_mix)
    mix_summary_row.pack(fill="x")
    mix_summary_row.columnconfigure(0, weight=1)
    mix_summary_row.columnconfigure(1, weight=1)

    avg_frame = ttk.LabelFrame(mix_summary_row, text=" Podsumowanie mixu ", padding=10)
    avg_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    avg_full_cost_monthly = tk.StringVar(value="—")
    avg_revenue_gross_monthly = tk.StringVar(value="—")
    avg_monthly = tk.StringVar(value="—")
    avg_net_monthly = tk.StringVar(value="—")
    avg_work_time = tk.StringVar(value="—")
    mix_total_display = tk.StringVar(value="—")
    revenue_annual_display = tk.StringVar(value="")
    frames_per_day_var = tk.StringVar(value="1")
    frames_per_day_state: dict[str, bool] = {"syncing": False}
    frames_mode_var = tk.StringVar(value="manual")
    frames_per_day_hint = tk.StringVar(value="")
    ttk.Label(avg_frame, text="Suma sprzedaży:").grid(row=0, column=0, sticky="w", padx=(0, 8))
    ttk.Label(avg_frame, textvariable=mix_total_display, font=("Segoe UI", 10, "bold")).grid(
        row=0, column=1, sticky="w"
    )
    ttk.Label(avg_frame, text="Przychód brutto:").grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=(8, 0))
    revenue_col = ttk.Frame(avg_frame)
    revenue_col.grid(row=1, column=1, sticky="w", pady=(8, 0))
    ttk.Label(
        revenue_col,
        textvariable=avg_revenue_gross_monthly,
        font=("Segoe UI", 11, "bold"),
        foreground=_ACCENT,
    ).pack(anchor="w")
    ttk.Label(
        revenue_col,
        textvariable=revenue_annual_display,
        foreground="#888",
        font=("Segoe UI", 8),
    ).pack(anchor="w")
    ttk.Label(avg_frame, text="Koszt produkcji z wysyłką:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
    ttk.Label(avg_frame, textvariable=avg_full_cost_monthly, font=("Segoe UI", 11, "bold"), foreground="#c62828").grid(
        row=2, column=1, sticky="w", pady=(4, 0)
    )
    ttk.Label(avg_frame, text="Zysk brutto:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
    ttk.Label(avg_frame, textvariable=avg_monthly, font=("Segoe UI", 11, "bold"), foreground=_SUCCESS).grid(
        row=3, column=1, sticky="w", pady=(4, 0)
    )
    ttk.Label(avg_frame, text="Zysk netto (po kosztach JDG):").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
    ttk.Label(avg_frame, textvariable=avg_net_monthly, font=("Segoe UI", 10, "bold"), foreground="#2e7d32").grid(
        row=4, column=1, sticky="w", pady=(4, 0)
    )
    tax_form_tip = tk.StringVar(value="")
    tax_form_tip_lbl = ttk.Label(
        avg_frame,
        textvariable=tax_form_tip,
        wraplength=380,
        justify="left",
        font=("Segoe UI", 8),
        foreground="#e65100",
    )
    tax_form_tip_lbl.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))
    ttk.Label(avg_frame, text="Czas pracy:").grid(row=6, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
    ttk.Label(avg_frame, textvariable=avg_work_time, font=("Segoe UI", 10, "bold")).grid(
        row=6, column=1, sticky="w", pady=(4, 0)
    )
    ttk.Label(avg_frame, text="Ramek na dzień:").grid(row=7, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
    frames_per_day_row = ttk.Frame(avg_frame)
    frames_per_day_row.grid(row=7, column=1, sticky="w", pady=(4, 0))
    frames_per_day_minus_btn = ttk.Button(frames_per_day_row, text="−", width=3)
    frames_per_day_minus_btn.pack(side="left")
    ttk.Label(
        frames_per_day_row,
        textvariable=frames_per_day_var,
        width=8,
        anchor="center",
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left", padx=(4, 4))
    frames_per_day_plus_btn = ttk.Button(frames_per_day_row, text="+", width=3)
    frames_per_day_plus_btn.pack(side="left")
    frames_mode_row = ttk.Frame(avg_frame)
    frames_mode_row.grid(row=8, column=0, columnspan=2, sticky="w", pady=(6, 0))
    ttk.Radiobutton(
        frames_mode_row,
        text="Ręcznie",
        variable=frames_mode_var,
        value="manual",
    ).pack(side="left", padx=(0, 12))
    ttk.Radiobutton(
        frames_mode_row,
        text="Z czasu produkcji (Kalkulator)",
        variable=frames_mode_var,
        value="calculator",
    ).pack(side="left")
    ttk.Label(avg_frame, textvariable=frames_per_day_hint, foreground="#666", font=("Segoe UI", 8)).grid(
        row=9, column=0, columnspan=2, sticky="w", pady=(4, 0)
    )

    variant_profit_frame = ttk.LabelFrame(
        mix_summary_row,
        text=" Zysk wg wariantów (zysk × szt.) ",
        padding=10,
    )
    variant_profit_frame.grid(row=0, column=1, sticky="nsew")
    variant_profit_lbls: list[tk.StringVar] = []
    for i in range(6):
        var = tk.StringVar(value="—")
        variant_profit_lbls.append(var)
        ttk.Label(variant_profit_frame, textvariable=var, font=("Segoe UI", 9)).grid(
            row=i, column=0, sticky="w", pady=1
        )
    variant_profit_total = tk.StringVar(value="—")
    ttk.Label(
        variant_profit_frame,
        textvariable=variant_profit_total,
        font=("Segoe UI", 10, "bold"),
        foreground=_ACCENT,
    ).grid(row=6, column=0, sticky="w", pady=(8, 0))

    # --- Drewno ---
    wood_inner, wood_canvas = _scrollable(tab_wood)
    wood_params = ttk.LabelFrame(wood_inner, text=" Parametry ", padding=10)
    wood_params.pack(fill="x", pady=(0, 8))
    w_species = tk.StringVar(value="SOSNA")
    w_fmt = tk.StringVar(value="A4")
    w_shipping = tk.StringVar(value="25")
    w_price = tk.StringVar(value="")
    w_pieces = tk.StringVar(value="")
    w_opt_batch = tk.StringVar(value="—")
    w_opt_cost = tk.StringVar(value="—")

    ttk.Label(wood_params, text="Gatunek:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(wood_params, textvariable=w_species, values=list(WOODS), width=10, state="readonly").grid(
        row=0, column=1, sticky="w", padx=(4, 16)
    )
    ttk.Label(wood_params, text="Format:").grid(row=0, column=2, sticky="w")
    ttk.Combobox(wood_params, textvariable=w_fmt, values=list(FORMATS), width=8, state="readonly").grid(
        row=0, column=3, sticky="w", padx=(4, 16)
    )
    ttk.Label(wood_params, text="Przesyłka (zł):").grid(row=0, column=4, sticky="w")
    ttk.Entry(wood_params, textvariable=w_shipping, width=8).grid(row=0, column=5, sticky="w", padx=(4, 0))

    ttk.Label(wood_params, text="Cena za mb:").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Label(wood_params, textvariable=w_price).grid(row=1, column=1, sticky="w", pady=(8, 0))
    ttk.Label(wood_params, text="Odcinki / szt.:").grid(row=1, column=2, sticky="w", pady=(8, 0))
    ttk.Label(wood_params, textvariable=w_pieces).grid(row=1, column=3, sticky="w", pady=(8, 0))
    ttk.Label(wood_params, text="Opt. partia:").grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Label(wood_params, textvariable=w_opt_batch, font=("Segoe UI", 10, "bold")).grid(
        row=2, column=1, sticky="w", pady=(8, 0)
    )
    ttk.Label(wood_params, text="Koszt / szt.:").grid(row=2, column=2, sticky="w", pady=(8, 0))
    ttk.Label(wood_params, textvariable=w_opt_cost, font=("Segoe UI", 11, "bold"), foreground=_ACCENT).grid(
        row=2, column=3, sticky="w", pady=(8, 0)
    )
    apply_wood_btn = ttk.Button(wood_params, text="Zastosuj koszt drewna w kalkulatorze")
    apply_wood_btn.grid(row=2, column=4, columnspan=2, sticky="e", pady=(8, 0))

    wood_table = ttk.Treeview(
        wood_inner,
        columns=("batch", "meters", "wood", "ship", "cpf"),
        show="headings",
        height=12,
    )
    for col, title in [
        ("batch", "Partia (szt.)"),
        ("meters", "Metry"),
        ("wood", "Koszt drewna"),
        ("ship", "Przesyłka"),
        ("cpf", "Koszt / szt."),
    ]:
        wood_table.heading(col, text=title)
        wood_table.column(col, width=100, anchor="e" if col != "batch" else "center")
    wood_table.pack(fill="both", expand=True, pady=(8, 0))
    bind_mousewheel_to_canvas(wood_canvas, wood_inner)

    # --- Materiały ---
    mat_filter = tk.StringVar(value="")
    mat_top = ttk.Frame(tab_materials)
    mat_top.pack(fill="x", pady=(0, 6))
    ttk.Label(mat_top, text="Szukaj:").pack(side="left")
    ttk.Entry(mat_top, textvariable=mat_filter, width=30).pack(side="left", padx=(6, 0))
    save_mat_btn = ttk.Button(mat_top, text="Zapisz zmiany cen")
    save_mat_btn.pack(side="right")

    mat_tree = ttk.Treeview(
        tab_materials,
        columns=("id", "category", "product", "size", "price"),
        show="headings",
        height=18,
    )
    for col, title, w in [
        ("id", "ID", 140),
        ("category", "Kategoria", 100),
        ("product", "Towar", 160),
        ("size", "Rozmiar", 80),
        ("price", "Cena", 80),
    ]:
        mat_tree.heading(col, text=title)
        mat_tree.column(col, width=w, anchor="w" if col != "price" else "e")
    mat_tree.pack(fill="both", expand=True)
    mat_status = tk.StringVar(value="")
    ttk.Label(tab_materials, textvariable=mat_status, foreground="#555").pack(anchor="w", pady=(4, 0))

    business_tab_state: dict[str, object] = {}

    def _on_business_costs_change() -> None:
        refresh_mix()

    # --- Koszty działalności ---
    business_tab_state.update(
        build_business_costs_tab(tab_business, on_change=_on_business_costs_change)
    )

    # --- Import ---
    import_path = tk.StringVar(
        value=r"c:\Users\Skarabeusz\Downloads\do analizy.xlsm"
    )
    imp_inner, _ = _scrollable(tab_import)
    ttk.Label(
        imp_inner,
        text="Importuj dane z pliku .xlsm (CENNIK MATERIAŁÓW, TABELA CEN, CENNIK, KALKULATOR DREWNA).",
        wraplength=680,
    ).pack(anchor="w", pady=(0, 8))
    imp_row = ttk.Frame(imp_inner)
    imp_row.pack(fill="x", pady=(0, 8))
    ttk.Entry(imp_row, textvariable=import_path, width=70).pack(side="left", fill="x", expand=True, padx=(0, 8))

    def browse_xlsm() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz plik Excel",
            filetypes=[("Excel macro", "*.xlsm"), ("Excel", "*.xlsx"), ("Wszystkie", "*.*")],
        )
        if path:
            import_path.set(path)

    ttk.Button(imp_row, text="Przeglądaj…", command=browse_xlsm).pack(side="left")
    import_btn = ttk.Button(imp_inner, text="Importuj do kalkulatora")
    import_btn.pack(anchor="w", pady=(0, 8))
    import_status = tk.StringVar(value="Dane wbudowane z do analizy.xlsm (czerwiec 2026).")
    ttk.Label(imp_inner, textvariable=import_status, foreground="#444", wraplength=680).pack(anchor="w")

    # --- Logika odświeżania ---
    material_rows: list[dict] = []
    last_wood_opt = None

    def _parse_num(raw: str) -> float | None:
        text = raw.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _set_pricing_fields(snap: dict[str, float], *, skip: str | None = None) -> None:
        pricing_state["syncing"] = True
        if skip != "price":
            price_var.set(f"{snap['sell_price']:.2f}")
        if skip != "markup":
            markup_var.set(f"{snap['markup_pct']:.1f}")
        if skip != "margin":
            margin_var.set(f"{snap['margin_pct']:.1f}")
        pricing_state["syncing"] = False

    def _variant_label(wood: str, fmt: str) -> str:
        return f"Cennik wariantu: {wood} · {fmt}"

    def _load_production_time(wood: str, fmt: str) -> None:
        settings = load_settings()
        mins = resolve_production_minutes(wood, fmt, settings=settings)
        time_state["syncing"] = True
        time_var.set(fmt_production_hours(mins))
        time_state["syncing"] = False

    def _save_production_time(wood: str, fmt: str) -> None:
        hours = _parse_num(time_var.get())
        if hours is None or hours <= 0:
            return
        mins = production_minutes_from_hours(hours)
        settings = load_settings()
        vpm = dict(settings.get("variant_production_minutes") or {})
        vpm[sell_key(wood, fmt)] = mins
        settings["variant_production_minutes"] = vpm
        save_settings(settings)

    def _update_hourly(profit: float) -> None:
        hours = _parse_num(time_var.get())
        if hours is None or hours <= 0:
            hourly_lbl.set("—")
            return
        hourly_lbl.set(fmt_hourly(hourly_profit(profit, production_minutes_from_hours(hours))))

    def refresh_calc() -> None:
        if pricing_state["syncing"]:
            return
        wood = wood_var.get()
        fmt = fmt_var.get()
        pricing_frame.configure(text=_variant_label(wood, fmt))
        settings = load_settings()
        driver = pricing_state["driver"]

        sell = markup = margin = None
        if driver == "price":
            sell = _parse_num(price_var.get())
        elif driver == "markup":
            markup = _parse_num(markup_var.get())
        elif driver == "margin":
            margin = _parse_num(margin_var.get())

        result = compute_variant(
            wood,
            fmt,
            settings=settings,
            sell_price=sell,
            markup_pct=markup,
            margin_pct=margin,
            pricing_driver=str(driver) if driver else None,
        )
        pricing_state["total_cost"] = result.total_cost
        pricing_state["last_profit"] = result.profit
        snap = pricing_snapshot(result.total_cost, result.sell_price)

        if driver is None:
            _set_pricing_fields(snap)
        else:
            _set_pricing_fields(snap, skip=str(driver))

        cost_lbl.set(fmt_money(result.total_cost))
        full_cost_lbl.set(fmt_money(result.full_cost))
        price_lbl.set(fmt_money(result.sell_price))
        profit_lbl.set(fmt_money(result.profit))
        margin_lbl.set(fmt_pct(result.margin))
        markup_lbl.set(f"{snap['markup_pct']:.1f} %")
        _update_hourly(result.profit)
        sec_prod.set(fmt_money(result.production_total))
        sec_print.set(fmt_money(result.print_total))
        sec_pack.set(fmt_money(result.packaging_total))
        sec_ship.set(fmt_money(result.shipping_total))

        for item in breakdown.get_children():
            breakdown.delete(item)
        current_sec = ""
        for line in result.lines:
            sec_label = SECTION_LABELS.get(line.section, line.section)
            if sec_label != current_sec:
                tag = _BREAKDOWN_HEADER_TAGS.get(line.section, ("header_other", "", ""))[0]
                breakdown.insert("", "end", values=(f"— {sec_label} —", ""), tags=(tag,))
                current_sec = sec_label
            breakdown.insert("", "end", values=(line.name, fmt_money(line.cost)))

    def _on_variant_change(*_args: object) -> None:
        pricing_state["driver"] = None
        _load_production_time(wood_var.get(), fmt_var.get())
        refresh_calc()

    def _save_wood_origin() -> None:
        origin = wood_origin_var.get().strip()
        if origin not in WOOD_ORIGINS:
            return
        settings = load_settings()
        settings["wood_origin"] = origin
        save_settings(settings)

    def _on_wood_origin_change(*_args: object) -> None:
        _save_wood_origin()
        refresh_calc()
        refresh_mix()

    def _on_time_edit(*_args: object) -> None:
        if time_state["syncing"]:
            return
        wood = wood_var.get()
        fmt = fmt_var.get()
        profit = float(pricing_state.get("last_profit") or 0)
        _update_hourly(profit)
        _save_production_time(wood, fmt)
        refresh_mix()

    def _on_price_edit(*_args: object) -> None:
        if pricing_state["syncing"]:
            return
        pricing_state["driver"] = "price"
        refresh_calc()

    def _on_markup_edit(*_args: object) -> None:
        if pricing_state["syncing"]:
            return
        pricing_state["driver"] = "markup"
        refresh_calc()

    def _on_margin_edit(*_args: object) -> None:
        if pricing_state["syncing"]:
            return
        pricing_state["driver"] = "margin"
        refresh_calc()

    def refresh_mix() -> None:
        mix = resolved_sales_mix()
        for item in mix_tree.get_children():
            mix_tree.delete(item)
        for row in mix:
            key = sell_key(str(row.get("wood") or ""), str(row.get("format") or ""))
            weight = float(row.get("weight") or 0)
            weight_txt = f"{weight * 100:.0f} %" if abs(weight * 100 - round(weight * 100)) < 0.05 else f"{weight * 100:.1f} %"
            mix_tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    row.get("wood"),
                    row.get("format"),
                    fmt_money(row.get("sell_price")),
                    fmt_money(row.get("full_cost")),
                    fmt_money(row.get("profit")),
                    weight_txt,
                    row.get("units_label") or "",
                ),
            )
        _update_frames_per_day_ui(mix)
        _apply_mix_summary(mix)
        _load_mix_total(total_mix_units(mix))
        refresh_business = business_tab_state.get("refresh")
        if callable(refresh_business):
            refresh_business()
        notify_cost_structure_update()

    def _load_mix_total(total: int) -> None:
        mix_total_state["syncing"] = True
        mix_total_var.set(str(int(total)))
        mix_total_display.set(format_frame_count(total))
        mix_total_state["syncing"] = False

    def apply_mix_total() -> None:
        total = parse_mix_units(mix_total_var.get())
        if total is None:
            show_toast(root, "Podaj liczbę sprzedanych ramek", duration_ms=1800, bg="#a23b2a", fg="white")
            return
        save_sales_mix(redistribute_mix_total(load_sales_mix(), total))
        refresh_mix()

    def _current_frames_per_day_for_step() -> int:
        """Baza dla ±: wartość z pola; puste pole = 1."""
        if not frames_per_day_var.get().strip():
            return 1
        value = _parse_num(frames_per_day_var.get())
        if value is None:
            return 1
        return normalize_manual_frames_per_day(value)

    def _frames_per_day_for_calc() -> int:
        """Do podsumowania: wpisana wartość; puste pole = 1."""
        if frames_mode_var.get() != "manual":
            return normalize_manual_frames_per_day(load_settings().get("frames_per_day"))
        value = _parse_num(frames_per_day_var.get())
        if value is not None and value >= 1:
            return normalize_manual_frames_per_day(value)
        if not frames_per_day_var.get().strip():
            return 1
        return normalize_manual_frames_per_day(load_settings().get("frames_per_day"))

    def _apply_mix_summary(mix: list[dict[str, object]]) -> None:
        settings = load_settings()
        mode = frames_mode_var.get()
        fpd = _frames_per_day_for_calc()
        avg_monthly.set(fmt_monthly_profit_forecast(mix, settings=settings))
        avg_revenue_gross_monthly.set(fmt_monthly_revenue_forecast(mix, settings=settings))
        revenue_annual_display.set(
            f"Rocznie: {fmt_money(monthly_revenue_forecast(mix) * 12)}"
        )
        avg_full_cost_monthly.set(fmt_monthly_full_cost_forecast(mix, settings=settings))
        avg_net_monthly.set(fmt_monthly_net_forecast(mix, settings=settings))
        bc = load_business_costs(settings)
        if bc["enabled"]:
            comp = compare_tax_forms(
                bc,
                monthly_revenue=monthly_revenue_forecast(mix),
                monthly_production_cost=monthly_full_cost_forecast(mix),
            )
            msg = comp.get("message") or ""
            tax_form_tip.set(msg)
            if comp.get("ryczalt_better"):
                tax_form_tip_lbl.configure(foreground="#e65100")
            elif msg:
                tax_form_tip_lbl.configure(foreground="#1565c0")
            else:
                tax_form_tip_lbl.configure(foreground="#666")
        else:
            tax_form_tip.set("Włącz koszty JDG w zakładce „Koszty działalności”, aby porównać formy opodatkowania.")
            tax_form_tip_lbl.configure(foreground="#888")
        if mode == "calculator":
            avg_work_time.set(fmt_work_hours(monthly_work_hours(mix, settings=settings)))
        else:
            work_days = work_days_from_sales(
                mix,
                settings=settings,
                frames_per_day=fpd,
                mode="manual",
            )
            avg_work_time.set(fmt_work_days(work_days))
        for var, row in zip(variant_profit_lbls, mix, strict=True):
            profit = float(row.get("profit") or 0)
            units = int(row.get("units") or 0)
            wood = row.get("wood")
            fmt = row.get("format")
            var.set(f"{wood} {fmt}: {fmt_money(profit)} × {units} = {fmt_money(profit * units)}")
        variant_profit_total.set(f"Razem: {fmt_money(monthly_profit_forecast(mix))}")

    def apply_mix_change(delta: int, *, notify: bool = True) -> None:
        if delta == 0:
            return
        before = load_sales_mix()
        before_total = sum(int(row.get("units") or 0) for row in before)
        if delta < 0 and before_total <= 0:
            if notify:
                show_toast(root, "Mix jest pusty — nie można odejmować", duration_ms=2200, bg="#a23b2a", fg="white")
            return
        after = apply_sales_change(before, delta)
        after_total = sum(int(row.get("units") or 0) for row in after)
        actual = after_total - before_total
        if actual == 0:
            if notify:
                show_toast(root, "Brak zmian w mixie", duration_ms=1800, bg="#a23b2a", fg="white")
            return
        save_sales_mix(after)
        if notify:
            parts = []
            for i, row in enumerate(after):
                diff = int(row["units"]) - int(before[i]["units"])
                if diff != 0:
                    parts.append(f"{row['wood']} {row['format']} {diff:+d}")
            detail = ", ".join(parts)
            if actual > 0:
                msg = f"Dodano {actual} szt. wg udziału: {detail}"
                bg = _SUCCESS
            else:
                msg = f"Odjęto {-actual} szt. wg udziału: {detail}"
                bg = "#5a6a7a"
            show_toast(root, msg, duration_ms=3200, bg=bg, fg="white")
        refresh_mix()

    def apply_mix_step(sign: int) -> None:
        amount = parse_mix_units(mix_growth_var.get())
        if amount is None or amount <= 0:
            if not mix_growth_var.get().strip():
                amount = 1
            else:
                show_toast(root, "Wpisz dodatnią liczbę sztuk w polu", duration_ms=1800, bg="#a23b2a", fg="white")
                return
        apply_mix_change(amount * sign, notify=False)

    def apply_mix_bulk() -> None:
        apply_mix_step(1)

    def apply_mix_growth() -> None:
        apply_mix_step(1)

    def apply_mix_decline() -> None:
        apply_mix_step(-1)

    def _load_frames_mode() -> None:
        mode = str(load_settings().get("frames_per_day_mode") or "manual")
        if mode not in ("manual", "calculator"):
            mode = "manual"
        frames_mode_var.set(mode)

    def _save_frames_mode() -> None:
        settings = load_settings()
        settings["frames_per_day_mode"] = frames_mode_var.get()
        save_settings(settings)

    def _update_frames_per_day_ui(mix: list[dict[str, object]] | None = None) -> None:
        settings = load_settings()
        mode = frames_mode_var.get()
        total_frames = total_mix_units(mix)
        if mode == "calculator":
            frames_per_day_minus_btn.configure(state="disabled")
            frames_per_day_plus_btn.configure(state="disabled")
            avg_hours = weighted_production_hours_per_frame(mix, settings=settings)
            work_day = float(settings.get("work_hours_per_day") or 8.0)
            value = frames_per_day_from_calculator(mix, settings=settings)
            frames_per_day_state["syncing"] = True
            frames_per_day_var.set(_format_frames_per_day(value))
            frames_per_day_state["syncing"] = False
            work_hours = monthly_work_hours(mix, settings=settings)
            work_txt = fmt_work_hours(work_hours)
            frames_per_day_hint.set(
                (
                    f"Śr. {avg_hours:.2f} h/ramkę · {work_day:g} h/dzień · "
                    f"czas produkcji mixu: {work_txt}"
                ).replace(".", ",")
            )
        else:
            frames_per_day_minus_btn.configure(state="normal")
            frames_per_day_plus_btn.configure(state="normal")
            fpd = _frames_per_day_for_calc()
            work_days = work_days_from_sales(
                mix,
                settings=settings,
                frames_per_day=fpd,
                mode="manual",
            )
            work_txt = fmt_work_days(work_days) if work_days is not None else "—"
            frames_per_day_hint.set(
                f"{format_frame_count(total_frames)} ÷ {fpd} = {work_txt}"
            )

    def _on_frames_mode_change(*_args: object) -> None:
        mode = frames_mode_var.get()
        if mode == "manual":
            settings = load_settings()
            rounded = normalize_manual_frames_per_day(settings.get("frames_per_day"))
            if rounded != settings.get("frames_per_day"):
                settings["frames_per_day"] = rounded
                save_settings(settings)
            _load_frames_per_day()
        _save_frames_mode()
        mix = resolved_sales_mix()
        _update_frames_per_day_ui(mix)
        _apply_mix_summary(mix)

    def _format_frames_per_day(value: float) -> str:
        return str(normalize_manual_frames_per_day(value))

    def _load_frames_per_day() -> None:
        value = normalize_manual_frames_per_day(load_settings().get("frames_per_day"))
        frames_per_day_state["syncing"] = True
        frames_per_day_var.set(_format_frames_per_day(value))
        frames_per_day_state["syncing"] = False

    def _save_frames_per_day() -> None:
        value = _parse_num(frames_per_day_var.get())
        if value is None or value < 1:
            return
        settings = load_settings()
        settings["frames_per_day"] = normalize_manual_frames_per_day(value)
        save_settings(settings)

    def apply_frames_per_day_step(delta: float) -> None:
        if frames_mode_var.get() != "manual":
            return
        new_val = max(1, _current_frames_per_day_for_step() + int(delta))
        frames_per_day_state["syncing"] = True
        frames_per_day_var.set(_format_frames_per_day(new_val))
        frames_per_day_state["syncing"] = False
        _save_frames_per_day()
        mix = resolved_sales_mix()
        _update_frames_per_day_ui(mix)
        _apply_mix_summary(mix)

    def refresh_wood() -> None:
        nonlocal last_wood_opt
        try:
            shipping = float(w_shipping.get().replace(",", "."))
        except ValueError:
            shipping = 25.0
        opt = wood_cost_for_variant(w_species.get(), w_fmt.get(), shipping=shipping)
        last_wood_opt = opt
        w_price.set(fmt_money(opt.price_per_meter))
        w_pieces.set(str(opt.pieces_per_frame))
        w_opt_batch.set(str(opt.optimal_batch))
        w_opt_cost.set(fmt_money(opt.optimal_cost_per_frame))
        for item in wood_table.get_children():
            wood_table.delete(item)
        for row in opt.rows:
            tags = ("best",) if row.batch == opt.optimal_batch else ()
            wood_table.insert(
                "",
                "end",
                values=(
                    row.batch,
                    f"{row.meters:.1f}",
                    fmt_money(row.wood_cost),
                    fmt_money(row.shipping),
                    fmt_money(row.cost_per_frame),
                ),
                tags=tags,
            )
        wood_table.tag_configure("best", background="#e3f2fd")

    def refresh_materials() -> None:
        nonlocal material_rows
        material_rows = load_materials()
        q = mat_filter.get().strip().lower()
        for item in mat_tree.get_children():
            mat_tree.delete(item)
        shown = 0
        for row in material_rows:
            hay = " ".join(
                str(row.get(k) or "")
                for k in ("id", "category", "product", "size")
            ).lower()
            if q and q not in hay:
                continue
            mat_tree.insert(
                "",
                "end",
                iid=row["id"],
                values=(
                    row.get("id"),
                    row.get("category"),
                    row.get("product"),
                    row.get("size"),
                    f"{float(row.get('price') or 0):.2f}",
                ),
            )
            shown += 1
        mat_status.set(f"Pozycji: {shown} / {len(material_rows)}")

    def save_pricing() -> None:
        wood = wood_var.get()
        fmt = fmt_var.get()
        driver = pricing_state["driver"] or "price"
        cost = float(pricing_state["total_cost"] or 0)

        sell = markup = margin = None
        if driver == "price":
            sell = _parse_num(price_var.get())
        elif driver == "markup":
            markup = _parse_num(markup_var.get())
        elif driver == "margin":
            margin = _parse_num(margin_var.get())

        result = compute_variant(
            wood,
            fmt,
            sell_price=sell,
            markup_pct=markup,
            margin_pct=margin,
            pricing_driver=str(driver),
        )
        cost = result.total_cost
        snap = pricing_snapshot(cost, result.sell_price)
        if snap["sell_price"] <= 0:
            show_toast(root, "Ustaw poprawną cenę sprzedaży", duration_ms=2000, bg="#a23b2a", fg="white")
            return

        settings = load_settings()
        vp = dict(settings.get("variant_pricing") or {})
        vp[sell_key(wood, fmt)] = {
            **snap,
            "driver": driver,
        }
        settings["variant_pricing"] = vp
        if driver == "markup":
            settings["default_markup_pct"] = snap["markup_pct"]
        save_settings(settings)

        pricing_state["driver"] = None
        _set_pricing_fields(snap)
        pricing_state["total_cost"] = cost

        show_toast(
            root,
            f"Zapisano cenę {wood} {fmt}: {snap['sell_price']:.2f} zł "
            f"(narzut {snap['markup_pct']:.1f}%, marża {snap['margin_pct']:.1f}%)",
            duration_ms=2600,
            bg=_SUCCESS,
            fg="white",
        )
        refresh_calc()
        refresh_mix()

    def update_template_from_calculator() -> None:
        if pricing_state.get("driver"):
            save_pricing()

        try:
            result = sync_variant_template_prices(all_templates=True)
        except FileNotFoundError as exc:
            messagebox.showerror("Szablon wariantów", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Szablon wariantów", f"Nie udało się zaktualizować szablonu:\n{exc}")
            return

        if result.variants_updated == 0:
            show_toast(
                root,
                f"Szablon już zgodny z kalkulatorem ({result.variants_unchanged} wariantów).",
                duration_ms=2800,
                bg="#5a6a7a",
                fg="white",
            )
            return

        show_toast(
            root,
            result.summary(),
            duration_ms=3600,
            bg=_SUCCESS,
            fg="white",
        )

    def apply_wood_cost() -> None:
        if last_wood_opt is None:
            refresh_wood()
        if last_wood_opt is None:
            return
        lines = load_cost_lines()
        from .calculator import update_wood_line_cost

        updated = update_wood_line_cost(
            last_wood_opt.species,
            last_wood_opt.fmt,
            last_wood_opt.optimal_cost_per_frame,
            cost_lines=lines,
        )
        save_cost_lines(updated)
        show_toast(
            root,
            f"Zaktualizowano drewno {last_wood_opt.species} {last_wood_opt.fmt}: "
            f"{fmt_money(last_wood_opt.optimal_cost_per_frame)}",
            duration_ms=2400,
            bg=_SUCCESS,
            fg="white",
        )
        refresh_calc()

    def save_material_prices() -> None:
        for iid in mat_tree.get_children():
            vals = mat_tree.item(iid, "values")
            try:
                price = float(str(vals[4]).replace(",", "."))
            except (ValueError, IndexError):
                continue
            for row in material_rows:
                if row.get("id") == iid:
                    row["price"] = price
                    break
        save_materials(material_rows)
        show_toast(root, "Zapisano ceny materiałów", duration_ms=1800, bg=_SUCCESS, fg="white")
        refresh_wood()

    def on_mat_double_click(event: tk.Event) -> None:
        item = mat_tree.identify_row(event.y)
        col = mat_tree.identify_column(event.x)
        if not item or col != "#5":
            return
        x, y, w, h = mat_tree.bbox(item, col)
        old = mat_tree.set(item, "price")

        entry = ttk.Entry(mat_tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, old)
        entry.focus_set()

        def commit(_evt: object = None) -> None:
            mat_tree.set(item, "price", entry.get())
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

    def on_mix_double_click(event: tk.Event) -> None:
        item = mix_tree.identify_row(event.y)
        col = mix_tree.identify_column(event.x)
        if not item or col != "#7":
            return
        x, y, w, h = mix_tree.bbox(item, col)
        old = mix_tree.set(item, "units")

        entry = ttk.Entry(mix_tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, old)
        entry.focus_set()
        entry.select_range(0, "end")

        def commit(_evt: object = None) -> None:
            new_units = parse_mix_units(entry.get())
            entry.destroy()
            if new_units is None:
                show_toast(root, "Podaj liczbę całkowitą sztuk", duration_ms=1800, bg="#a23b2a", fg="white")
                return
            before = load_sales_mix()
            base = normalize_sales_mix(before)
            old_units = 0
            for row in base:
                if sell_key(row["wood"], row["format"]) == item:
                    old_units = int(row.get("units") or 0)
                    break
            delta = new_units - old_units
            if delta == 0:
                return
            save_sales_mix(apply_sales_change(before, delta))
            refresh_mix()

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

    def do_import() -> None:
        try:
            stats = import_from_xlsm(import_path.get())
        except Exception as exc:
            messagebox.showerror("Import", str(exc), parent=root)
            return
        import_status.set(
            f"Zaimportowano: {stats['materials']} materiałów, "
            f"{stats['price_table']} pozycji tabeli cen, "
            f"{stats['cost_lines']} wierszy kosztów."
        )
        show_toast(root, "Import zakończony", duration_ms=2000, bg=_SUCCESS, fg="white")
        refresh_all()

    def refresh_all() -> None:
        refresh_calc()
        refresh_mix()
        refresh_wood()
        refresh_materials()

    save_price_btn.configure(command=save_pricing)
    update_tpl_btn.configure(command=update_template_from_calculator)
    mix_growth_plus_btn.configure(command=apply_mix_growth)
    mix_growth_minus_btn.configure(command=apply_mix_decline)
    mix_growth_entry.bind("<Return>", lambda _evt: apply_mix_bulk())
    mix_total_btn.configure(command=apply_mix_total)
    mix_total_entry.bind("<Return>", lambda _evt: apply_mix_total())
    frames_per_day_plus_btn.configure(command=lambda: apply_frames_per_day_step(1))
    frames_per_day_minus_btn.configure(command=lambda: apply_frames_per_day_step(-1))
    apply_wood_btn.configure(command=apply_wood_cost)
    save_mat_btn.configure(command=save_material_prices)
    import_btn.configure(command=do_import)
    mat_tree.bind("<Double-1>", on_mat_double_click)
    mix_tree.bind("<Double-1>", on_mix_double_click)

    for var in (wood_var, fmt_var):
        var.trace_add("write", _on_variant_change)
    wood_origin_var.trace_add("write", _on_wood_origin_change)
    price_var.trace_add("write", _on_price_edit)
    markup_var.trace_add("write", _on_markup_edit)
    margin_var.trace_add("write", _on_margin_edit)
    time_var.trace_add("write", _on_time_edit)
    frames_mode_var.trace_add("write", _on_frames_mode_change)
    for var in (w_species, w_fmt, w_shipping):
        var.trace_add("write", lambda *_: refresh_wood())
    mat_filter.trace_add("write", lambda *_: refresh_materials())

    _load_production_time(wood_var.get(), fmt_var.get())
    _load_frames_mode()
    _update_frames_per_day_ui(resolved_sales_mix())
    wood_origin_var.set(str(load_settings().get("wood_origin") or "stolarz24"))
    root.after(80, refresh_all)
    return root
