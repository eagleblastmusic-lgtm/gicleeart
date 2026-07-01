"""Widok inline — kalkulator passe-partout (Tkinter w launcherze)."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import ttk

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast

from .calculations import (
    DEFAULTS,
    ROUNDING_MODE_LABELS,
    SIZE_PRESETS,
    STRIPE_LABELS,
    CalculationInput,
    SavedLineItem,
    StripeLayout,
    analyze_quantity_table,
    build_multi_seller_message,
    build_seller_message,
    calculate_order_result,
    calculate_quantity_table,
    calculate_single_piece_metrics,
    combine_saved_lines,
    compare_rounding_modes,
    format_saved_line_label,
    fmt_area,
    fmt_money,
    fmt_number,
    normalize_dimensions,
    parse_number,
    validate_input,
)

_ACCENT = "#6b4423"
_WARN = "#9a3412"
_SUCCESS = "#2f6b4f"
_ALLEGRO_ORDER_URL = (
    "https://allegro.pl/produkt/passe-partout-bialy-10-cm-x-10-cm-"
    "74ebcf0a-3951-465f-9d05-45cf1df95638?offerId=14558509948"
)


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


def _labeled_entry(parent: tk.Misc, row: int, col: int, label: str, var: tk.StringVar) -> ttk.Entry:
    ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="w", padx=(0, 8), pady=4)
    entry = ttk.Entry(parent, textvariable=var, width=14, font=("Segoe UI", 11))
    entry.grid(row=row, column=col * 2 + 1, sticky="ew", pady=4)
    return entry


def _result_line(parent: tk.Misc, row: int, label: str, var: tk.StringVar, *, big: bool = False) -> None:
    font = ("Segoe UI", 12, "bold") if big else ("Segoe UI", 10)
    ttk.Label(parent, text=label, foreground="#555").grid(row=row, column=0, sticky="w", pady=2)
    ttk.Label(parent, textvariable=var, font=font).grid(row=row, column=1, sticky="e", pady=2)


def _collapsible_section(
    parent: tk.Misc,
    row: int,
    title: str,
    *,
    expanded: bool = False,
    on_toggle: Callable[[], None] | None = None,
) -> tuple[ttk.Frame, ttk.Frame]:
    """Nagłówek z przyciskiem rozwijania + zwijana treść."""
    shell = ttk.Frame(parent)
    shell.grid(row=row, column=0, sticky="ew", pady=(0, 8))
    shell.columnconfigure(0, weight=1)

    state = {"open": expanded}
    toggle_btn = ttk.Button(shell)
    toggle_btn.grid(row=0, column=0, sticky="ew")

    border = ttk.Frame(shell, relief="groove", borderwidth=1)
    border.grid(row=1, column=0, sticky="ew")
    border.columnconfigure(0, weight=1)
    inner_body = ttk.Frame(border, padding=(10, 8))
    inner_body.grid(row=0, column=0, sticky="ew")
    inner_body.columnconfigure(1, weight=1)
    inner_body.columnconfigure(3, weight=1)

    def _sync() -> None:
        arrow = "▼" if state["open"] else "▶"
        toggle_btn.configure(text=f"{arrow}  {title}")
        if state["open"]:
            border.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        else:
            border.grid_remove()

    def _toggle() -> None:
        state["open"] = not state["open"]
        _sync()
        if on_toggle is not None:
            on_toggle()

    toggle_btn.configure(command=_toggle)
    _sync()
    return shell, inner_body


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    root = ttk.Frame(parent)
    root.pack(fill="both", expand=True)

    header = ttk.Frame(root, padding=(12, 10, 12, 6))
    header.pack(fill="x")
    ttk.Button(header, text="← Wróć", command=on_back).pack(side="left")
    ttk.Label(header, text="Passe-partout", font=("Segoe UI", 14, "bold")).pack(side="left", padx=(12, 0))
    ttk.Label(
        header,
        text="Kalkulator jednostek Allegro",
        foreground="#666",
        font=("Segoe UI", 9),
    ).pack(side="left", padx=(10, 0))
    ttk.Button(
        header,
        text="Zamów",
        command=lambda: webbrowser.open(_ALLEGRO_ORDER_URL),
    ).pack(side="right")

    scroll_host = ttk.Frame(root, padding=(12, 0, 12, 12))
    scroll_host.pack(fill="both", expand=True)
    inner, scroll_canvas = _scrollable(scroll_host)
    inner.columnconfigure(0, weight=1)

    def refresh_scroll() -> None:
        inner.update_idletasks()
        bbox = scroll_canvas.bbox("all")
        if bbox:
            scroll_canvas.configure(scrollregion=bbox)

    # --- Zmienne formularza ---
    vars_map = {
        "outer_w": tk.StringVar(value=str(DEFAULTS["outer_width_cm"])),
        "outer_h": tk.StringVar(value=str(DEFAULTS["outer_height_cm"])),
        "win_w": tk.StringVar(value=str(DEFAULTS["window_width_cm"])),
        "win_h": tk.StringVar(value=str(DEFAULTS["window_height_cm"])),
        "qty": tk.StringVar(value=str(DEFAULTS["quantity"])),
        "price_m2": tk.StringVar(value=str(DEFAULTS["price_per_m2"])),
        "unit_price": tk.StringVar(value=str(DEFAULTS["unit_price"])),
        "free_ship": tk.StringVar(value=str(DEFAULTS["free_shipping_threshold"])),
        "ship_cost": tk.StringVar(value=str(DEFAULTS["shipping_cost"])),
    }
    stripe_var = tk.StringVar(value=DEFAULTS["stripe_layout"])
    rounding_var = tk.StringVar(value=DEFAULTS["rounding_mode"])

    # --- Wyniki (StringVar) ---
    warn_var = tk.StringVar(value="")
    units_highlight = tk.StringVar(value="—")
    units_sub = tk.StringVar(value="")

    piece_vars = {k: tk.StringVar(value="—") for k in (
        "area", "real", "raw_units", "round_units", "loss",
    )}
    order_vars = {k: tk.StringVar(value="—") for k in (
        "no_ship", "ship", "total", "per_piece", "loss",
    )}
    compare_vars = {
        "per_units": tk.StringVar(value="—"),
        "per_total": tk.StringVar(value="—"),
        "per_loss": tk.StringVar(value="—"),
        "batch_units": tk.StringVar(value="—"),
        "batch_total": tk.StringVar(value="—"),
        "batch_loss": tk.StringVar(value="—"),
        "verdict": tk.StringVar(value=""),
    }
    insights_var = tk.StringVar(value="")
    message_var = tk.StringVar(value="")
    combined_var = tk.StringVar(value="Brak zapisanych pozycji — użyj „Zapisz do zamówienia”.")

    order_state: dict[str, list[SavedLineItem]] = {"items": []}

    # --- Presety ---
    preset_row = ttk.Frame(inner)
    preset_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(preset_row, text="Format:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 8))

    def apply_preset(preset_id: str) -> None:
        preset = next((p for p in SIZE_PRESETS if p["id"] == preset_id), None)
        if not preset:
            return
        vars_map["outer_w"].set(str(preset["outer_width_cm"]))
        vars_map["outer_h"].set(str(preset["outer_height_cm"]))
        if preset["window_width_cm"] is not None:
            vars_map["win_w"].set(str(preset["window_width_cm"]))
        if preset["window_height_cm"] is not None:
            vars_map["win_h"].set(str(preset["window_height_cm"]))

    for preset in SIZE_PRESETS:
        ttk.Button(
            preset_row,
            text=preset["label"],
            command=lambda pid=preset["id"]: apply_preset(pid),
            width=10,
        ).pack(side="left", padx=(0, 4))

    # --- Formularz wymiarów ---
    form = ttk.LabelFrame(inner, text="  Wymiary i zamówienie  ", padding=(10, 8))
    form.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    form.columnconfigure(1, weight=1)
    form.columnconfigure(3, weight=1)

    outer_w_entry = _labeled_entry(form, 0, 0, "Szer. zewnętrzna (cm)", vars_map["outer_w"])
    outer_h_entry = _labeled_entry(form, 1, 0, "Wys. zewnętrzna (cm)", vars_map["outer_h"])
    win_w_entry = _labeled_entry(form, 0, 1, "Szer. okienka (cm)", vars_map["win_w"])
    win_h_entry = _labeled_entry(form, 1, 1, "Wys. okienka (cm)", vars_map["win_h"])
    _labeled_entry(form, 2, 0, "Liczba sztuk", vars_map["qty"])

    ttk.Label(form, text="Układ prążków").grid(row=2, column=2, sticky="nw", padx=(0, 8), pady=4)
    stripe_frame = ttk.Frame(form)
    stripe_frame.grid(row=2, column=3, sticky="w", pady=4)
    for layout, label in (("horizontal", "Prążki poziome"), ("vertical", "Prążki pionowe")):
        ttk.Radiobutton(
            stripe_frame,
            text=label,
            variable=stripe_var,
            value=layout,
        ).pack(side="left", padx=(0, 12))

    def _dim_str(value: float) -> str:
        rounded = round(value, 1)
        if abs(rounded - round(rounded)) < 1e-9:
            return str(int(round(rounded)))
        return str(rounded)

    def _sync_dim_pair(w_var: tk.StringVar, h_var: tk.StringVar) -> None:
        w, h = normalize_dimensions(parse_number(w_var.get()), parse_number(h_var.get()))
        w_var.set(_dim_str(w))
        h_var.set(_dim_str(h))

    def _bind_dim_sync(w_entry: ttk.Entry, h_entry: ttk.Entry, w_var: tk.StringVar, h_var: tk.StringVar) -> None:
        def _sync(_evt: object = None) -> None:
            _sync_dim_pair(w_var, h_var)

        for entry in (w_entry, h_entry):
            entry.bind("<FocusOut>", _sync)

    _bind_dim_sync(outer_w_entry, outer_h_entry, vars_map["outer_w"], vars_map["outer_h"])
    _bind_dim_sync(win_w_entry, win_h_entry, vars_map["win_w"], vars_map["win_h"])

    form_btns = ttk.Frame(form)
    form_btns.grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

    warn_lbl = ttk.Label(form, textvariable=warn_var, foreground=_WARN, wraplength=700)
    warn_lbl.grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

    # --- Zapisane pozycje ---
    saved_box = ttk.LabelFrame(inner, text="  Zapisane pozycje zamówienia  ", padding=(10, 8))
    saved_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
    saved_box.columnconfigure(0, weight=1)
    ttk.Label(saved_box, textvariable=combined_var, foreground="#444", wraplength=720).pack(
        anchor="w", pady=(0, 6)
    )

    saved_cols = ("outer", "window", "qty", "units", "stripes")
    saved_tree = ttk.Treeview(saved_box, columns=saved_cols, show="headings", height=4)
    for col, text, width in (
        ("outer", "Zewnętrzny", 100),
        ("window", "Okienko", 100),
        ("qty", "Szt.", 44),
        ("units", "Jednostki", 72),
        ("stripes", "Prążki", 120),
    ):
        saved_tree.heading(col, text=text)
        saved_tree.column(col, width=width, anchor="center")
    saved_vsb = ttk.Scrollbar(saved_box, orient="vertical", command=saved_tree.yview)
    saved_tree.configure(yscrollcommand=saved_vsb.set)
    saved_tree.pack(side="left", fill="x", expand=True)
    saved_vsb.pack(side="right", fill="y")

    def _saved_tree_wheel(evt: tk.Event) -> str:
        if evt.delta:
            saved_tree.yview_scroll(int(-evt.delta / 120), "units")
        elif evt.num == 4:
            saved_tree.yview_scroll(-1, "units")
        elif evt.num == 5:
            saved_tree.yview_scroll(1, "units")
        return "break"

    for _seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        saved_tree.bind(_seq, _saved_tree_wheel)

    # --- Ceny (zwijane) ---
    _, price_box = _collapsible_section(
        inner, 3, "Ceny i dostawa", expanded=False, on_toggle=refresh_scroll
    )
    _labeled_entry(price_box, 0, 0, "Cena za m² (zł)", vars_map["price_m2"])
    _labeled_entry(price_box, 0, 1, "Cena jednostki Allegro (zł)", vars_map["unit_price"])
    _labeled_entry(price_box, 1, 0, "Próg darmowej dostawy (zł)", vars_map["free_ship"])
    _labeled_entry(price_box, 1, 1, "Koszt dostawy (zł)", vars_map["ship_cost"])

    # --- Tryb zaokrąglania (zwijany) ---
    _, mode_box = _collapsible_section(
        inner, 4, "Tryb liczenia", expanded=False, on_toggle=refresh_scroll
    )
    for mode, label in ROUNDING_MODE_LABELS.items():
        ttk.Radiobutton(
            mode_box,
            text=label,
            variable=rounding_var,
            value=mode,
        ).pack(anchor="w", pady=2)

    # --- Highlight ---
    highlight = tk.Frame(inner, bg=_ACCENT, padx=14, pady=12)
    highlight.grid(row=5, column=0, sticky="ew", pady=(0, 8))
    tk.Label(
        highlight,
        text="Ile zamówić na Allegro",
        bg=_ACCENT,
        fg="#e8d4bc",
        font=("Segoe UI", 9),
    ).pack(anchor="w")
    tk.Label(
        highlight,
        textvariable=units_highlight,
        bg=_ACCENT,
        fg="white",
        font=("Segoe UI", 22, "bold"),
    ).pack(anchor="w")
    tk.Label(
        highlight,
        textvariable=units_sub,
        bg=_ACCENT,
        fg="#f0e6d8",
        font=("Segoe UI", 9),
    ).pack(anchor="w")

    # --- Karty wyników ---
    cards = ttk.Frame(inner)
    cards.grid(row=6, column=0, sticky="ew", pady=(0, 8))
    cards.columnconfigure(0, weight=1)
    cards.columnconfigure(1, weight=1)

    piece_card = ttk.LabelFrame(cards, text="  Jedna sztuka  ", padding=(10, 8))
    piece_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    piece_card.columnconfigure(1, weight=1)
    for i, (key, lbl) in enumerate((
        ("area", "Powierzchnia"),
        ("real", "Realna cena (m²)"),
        ("raw_units", "Jednostki przed zaokr."),
        ("round_units", "Jednostki po zaokr. / szt."),
        ("loss", "Strata przez zaokrąglenie / szt."),
    )):
        _result_line(piece_card, i, lbl, piece_vars[key])

    order_card = ttk.LabelFrame(cards, text="  Bieżąca pozycja  ", padding=(10, 8))
    order_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    order_card.columnconfigure(1, weight=1)
    for i, (key, lbl, big) in enumerate((
        ("no_ship", "Cena bez dostawy", True),
        ("ship", "Koszt dostawy", False),
        ("total", "Cena końcowa", True),
        ("per_piece", "Cena za 1 sztukę", True),
        ("loss", "Łączna strata na zaokrągleniu", False),
    )):
        _result_line(order_card, i, lbl, order_vars[key], big=big)

    # --- Porównanie trybów (zwijane) ---
    _, cmp_box = _collapsible_section(
        inner, 7, "Porównanie trybów liczenia", expanded=False, on_toggle=refresh_scroll
    )
    cmp_grid = ttk.Frame(cmp_box)
    cmp_grid.pack(fill="x")
    cmp_grid.columnconfigure(0, weight=1)
    cmp_grid.columnconfigure(1, weight=1)

    per_card = ttk.LabelFrame(cmp_grid, text="Każdą sztukę osobno", padding=(8, 6))
    per_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    ttk.Label(per_card, textvariable=compare_vars["per_units"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
    ttk.Label(per_card, textvariable=compare_vars["per_total"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(per_card, textvariable=compare_vars["per_loss"], foreground="#555").pack(anchor="w")

    batch_card = ttk.LabelFrame(cmp_grid, text="Całość razem", padding=(8, 6))
    batch_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    ttk.Label(batch_card, textvariable=compare_vars["batch_units"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
    ttk.Label(batch_card, textvariable=compare_vars["batch_total"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(batch_card, textvariable=compare_vars["batch_loss"], foreground="#555").pack(anchor="w")

    ttk.Label(cmp_box, textvariable=compare_vars["verdict"], foreground="#444", wraplength=720).pack(
        anchor="w", pady=(8, 0)
    )

    # --- Tabela ---
    table_box = ttk.LabelFrame(inner, text="  Tabela ilości (1–30 sztuk)  ", padding=(10, 8))
    table_box.grid(row=8, column=0, sticky="ew", pady=(0, 8))
    table_box.columnconfigure(0, weight=1)
    ttk.Label(table_box, textvariable=insights_var, foreground="#555", wraplength=720).pack(
        anchor="w", pady=(0, 6)
    )

    cols = ("qty", "units", "no_ship", "ship", "total", "per", "loss")
    tree = ttk.Treeview(table_box, columns=cols, show="headings", height=10)
    headings = (
        ("qty", "Szt.", 40),
        ("units", "Jednostki", 72),
        ("no_ship", "Bez dostawy", 90),
        ("ship", "Dostawa", 72),
        ("total", "Cena końcowa", 96),
        ("per", "Za 1 szt.", 88),
        ("loss", "Strata", 72),
    )
    for col, text, width in headings:
        tree.heading(col, text=text)
        tree.column(col, width=width, anchor="e" if col != "qty" else "center")
    tree.tag_configure("cheapest", background="#fff8e8")
    tree.tag_configure("free_ship", background="#e8f5ee")
    tree.tag_configure("current", font=("Segoe UI", 9, "bold"))
    vsb_tree = ttk.Scrollbar(table_box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb_tree.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb_tree.pack(side="right", fill="y")

    def _tree_wheel(evt: tk.Event) -> str:
        if evt.delta:
            tree.yview_scroll(int(-evt.delta / 120), "units")
        elif evt.num == 4:
            tree.yview_scroll(-1, "units")
        elif evt.num == 5:
            tree.yview_scroll(1, "units")
        return "break"

    for _seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        tree.bind(_seq, _tree_wheel)

    # --- Wiadomość ---
    msg_box = ttk.LabelFrame(inner, text="  Gotowa wiadomość do sprzedawcy  ", padding=(10, 8))
    msg_box.grid(row=9, column=0, sticky="ew", pady=(0, 4))
    msg_box.columnconfigure(0, weight=1)

    msg_text = tk.Text(msg_box, height=5, wrap="word", font=("Segoe UI", 10), relief="flat", bd=1)
    msg_text.pack(fill="x", pady=(0, 6))
    msg_text.configure(state="disabled")

    def copy_message() -> None:
        text = message_var.get()
        if not text:
            return
        top = root.winfo_toplevel()
        try:
            top.clipboard_clear()
            top.clipboard_append(text)
            show_toast(top, "Skopiowano do schowka", duration_ms=1800, bg=_SUCCESS, fg="white")
        except tk.TclError:
            show_toast(top, "Nie udało się skopiować", duration_ms=2000, bg="#a23b2a", fg="white")

    ttk.Button(msg_box, text="Kopiuj wiadomość", command=copy_message).pack(anchor="e")

    def _read_input() -> CalculationInput:
        qty_raw = parse_number(vars_map["qty"].get())
        qty = max(1, int(qty_raw)) if qty_raw >= 1 else 1
        unit_price = parse_number(vars_map["unit_price"].get())
        if unit_price <= 0:
            unit_price = DEFAULTS["unit_price"]
        outer_w, outer_h = normalize_dimensions(
            parse_number(vars_map["outer_w"].get()),
            parse_number(vars_map["outer_h"].get()),
        )
        win_w, win_h = normalize_dimensions(
            parse_number(vars_map["win_w"].get()),
            parse_number(vars_map["win_h"].get()),
        )
        return CalculationInput(
            outer_width_cm=outer_w,
            outer_height_cm=outer_h,
            window_width_cm=win_w,
            window_height_cm=win_h,
            quantity=qty,
            price_per_m2=parse_number(vars_map["price_m2"].get()),
            unit_price=unit_price,
            free_shipping_threshold=parse_number(vars_map["free_ship"].get()),
            shipping_cost=parse_number(vars_map["ship_cost"].get()),
            rounding_mode=rounding_var.get(),  # type: ignore[arg-type]
        )

    def recalculate() -> None:
        inp = _read_input()
        validation = validate_input(inp)
        warnings: list[str] = []
        if validation.window_too_large:
            warnings.append(
                "Uwaga: wymiar okienka jest większy niż wymiar zewnętrzny. "
                "Sprawdź, czy wartości są wpisane poprawnie."
            )
        if validation.has_negative_values:
            warnings.append("Wartości nie mogą być ujemne.")
        if validation.unit_price_invalid:
            warnings.append("Cena jednostki Allegro musi być większa od 0 zł.")
        if validation.quantity_invalid:
            warnings.append("Liczba sztuk musi wynosić co najmniej 1.")
        warn_var.set(" · ".join(warnings))

        metrics = calculate_single_piece_metrics(inp)
        order = calculate_order_result(inp)
        comparison = compare_rounding_modes(inp)
        rows = calculate_quantity_table(inp)
        insights = analyze_quantity_table(rows)

        stripe: StripeLayout = stripe_var.get()  # type: ignore[assignment]

        saved = order_state["items"]
        combined = combine_saved_lines(
            saved,
            free_shipping_threshold=inp.free_shipping_threshold,
            shipping_cost=inp.shipping_cost,
        )

        if combined is not None:
            units_highlight.set(f"{combined.total_units} jednostek")
            units_sub.set(
                f"Zamówienie: {len(saved)} pozycji · {combined.total_pieces} szt. łącznie"
            )
            ship_note = " (darmowa dostawa)" if combined.free_shipping_reached else ""
            combined_var.set(
                f"Łącznie: {combined.total_units} jednostek · "
                f"{fmt_money(combined.price_without_shipping)} bez dostawy · "
                f"{fmt_money(combined.shipping_cost_applied)} dostawa{ship_note} · "
                f"{fmt_money(combined.total_price)} końcowo · "
                f"strata {fmt_money(combined.rounding_loss)}"
            )
            msg = build_multi_seller_message(saved, combined)
        else:
            units_highlight.set(f"{order.units_total} jednostek")
            units_sub.set(
                f"{fmt_number(inp.outer_width_cm, 1)} × {fmt_number(inp.outer_height_cm, 1)} cm · "
                f"{inp.quantity} szt. · {STRIPE_LABELS[stripe]}"
            )
            combined_var.set("Brak zapisanych pozycji — użyj „Zapisz do zamówienia”.")
            msg = build_seller_message(
                quantity=inp.quantity,
                outer_width_cm=inp.outer_width_cm,
                outer_height_cm=inp.outer_height_cm,
                window_width_cm=inp.window_width_cm,
                window_height_cm=inp.window_height_cm,
                stripe_label=STRIPE_LABELS[stripe],
                units_total=order.units_total,
            )

        piece_vars["area"].set(fmt_area(metrics.area_m2))
        piece_vars["real"].set(fmt_money(metrics.real_price))
        piece_vars["raw_units"].set(fmt_number(metrics.units_raw, 2))
        piece_vars["round_units"].set(str(metrics.units_rounded_per_piece))
        piece_vars["loss"].set(fmt_money(metrics.loss_per_piece))

        ship_txt = fmt_money(order.shipping_cost_applied)
        if order.free_shipping_reached:
            ship_txt += " (darmowa dostawa)"

        display = combined if combined is not None else None
        if display is not None:
            order_card.configure(text="  Całe zamówienie  ")
            ship_txt = fmt_money(display.shipping_cost_applied)
            if display.free_shipping_reached:
                ship_txt += " (darmowa dostawa)"
            order_vars["no_ship"].set(fmt_money(display.price_without_shipping))
            order_vars["ship"].set(ship_txt)
            order_vars["total"].set(fmt_money(display.total_price))
            avg = display.total_price / display.total_pieces if display.total_pieces else 0.0
            order_vars["per_piece"].set(fmt_money(avg))
            order_vars["loss"].set(fmt_money(display.rounding_loss))
        else:
            order_card.configure(text="  Bieżąca pozycja  ")
            order_vars["no_ship"].set(fmt_money(order.price_without_shipping))
            order_vars["ship"].set(ship_txt)
            order_vars["total"].set(fmt_money(order.total_price))
            order_vars["per_piece"].set(fmt_money(order.price_per_piece))
            order_vars["loss"].set(fmt_money(order.rounding_loss))

        compare_vars["per_units"].set(f"{comparison.per_piece.units_total} jednostek")
        compare_vars["per_total"].set(fmt_money(comparison.per_piece.total_price))
        compare_vars["per_loss"].set(f"Strata: {fmt_money(comparison.per_piece.rounding_loss)}")
        compare_vars["batch_units"].set(f"{comparison.batch.units_total} jednostek")
        compare_vars["batch_total"].set(fmt_money(comparison.batch.total_price))
        compare_vars["batch_loss"].set(f"Strata: {fmt_money(comparison.batch.rounding_loss)}")

        if comparison.per_piece.total_price == comparison.batch.total_price:
            compare_vars["verdict"].set("Oba tryby kosztują tyle samo.")
        else:
            cheaper = ROUNDING_MODE_LABELS[comparison.cheaper_mode]
            compare_vars["verdict"].set(
                f"Tańszy: {cheaper} · różnica {fmt_money(comparison.price_difference)} · "
                f"{comparison.units_difference} jednostek Allegro"
            )

        insight_parts: list[str] = []
        if insights.cheapest_per_piece_quantity is not None:
            row = rows[insights.cheapest_per_piece_quantity - 1]
            insight_parts.append(
                f"Najtańsza za 1 szt.: {insights.cheapest_per_piece_quantity} szt. "
                f"({fmt_money(row.price_per_piece)})"
            )
        if insights.first_free_shipping_quantity is not None:
            insight_parts.append(
                f"Minimalna ilość do darmowej dostawy: {insights.first_free_shipping_quantity} szt."
            )
        if insights.most_profitable_quantity is not None:
            row = rows[insights.most_profitable_quantity - 1]
            insight_parts.append(
                f"Najbardziej opłacalna ilość: {insights.most_profitable_quantity} szt. "
                f"({fmt_money(row.total_price)} łącznie)"
            )
        insights_var.set(" · ".join(insight_parts))

        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            tags: list[str] = []
            if row.quantity == insights.cheapest_per_piece_quantity:
                tags.append("cheapest")
            if row.quantity == insights.first_free_shipping_quantity:
                tags.append("free_ship")
            if row.quantity == inp.quantity:
                tags.append("current")
            tree.insert(
                "",
                "end",
                values=(
                    row.quantity,
                    row.units_total,
                    fmt_money(row.price_without_shipping),
                    fmt_money(row.shipping_cost_applied),
                    fmt_money(row.total_price),
                    fmt_money(row.price_per_piece),
                    fmt_money(row.rounding_loss),
                ),
                tags=tuple(tags),
            )

        for item in saved_tree.get_children():
            saved_tree.delete(item)
        for idx, saved_item in enumerate(saved):
            outer, window, qty, units, stripes = format_saved_line_label(saved_item)
            saved_tree.insert("", "end", iid=str(idx), values=(outer, window, qty, units, stripes))

        message_var.set(msg)
        msg_text.configure(state="normal")
        msg_text.delete("1.0", "end")
        msg_text.insert("1.0", msg)
        msg_text.configure(state="disabled")
        refresh_scroll()

    def save_to_order() -> None:
        inp = _read_input()
        validation = validate_input(inp)
        top = root.winfo_toplevel()
        if validation.unit_price_invalid:
            show_toast(top, "Ustaw cenę jednostki Allegro > 0", duration_ms=2200, bg="#a23b2a", fg="white")
            return
        if validation.quantity_invalid:
            show_toast(top, "Liczba sztuk musi być co najmniej 1", duration_ms=2200, bg="#a23b2a", fg="white")
            return
        stripe: StripeLayout = stripe_var.get()  # type: ignore[assignment]
        order_state["items"].append(SavedLineItem(input=inp, stripe_layout=stripe))
        show_toast(
            top,
            f"Dodano pozycję ({inp.quantity} szt., "
            f"{fmt_number(inp.outer_width_cm, 1)}×{fmt_number(inp.outer_height_cm, 1)} cm)",
            duration_ms=2200,
            bg=_SUCCESS,
            fg="white",
        )
        recalculate()

    def remove_saved_line() -> None:
        sel = saved_tree.selection()
        if not sel:
            show_toast(root.winfo_toplevel(), "Zaznacz pozycję do usunięcia", duration_ms=1800, bg="#444", fg="white")
            return
        idx = int(sel[0])
        items = order_state["items"]
        if 0 <= idx < len(items):
            items.pop(idx)
            recalculate()

    def clear_order() -> None:
        if not order_state["items"]:
            return
        order_state["items"].clear()
        show_toast(root.winfo_toplevel(), "Wyczyszczono zamówienie", duration_ms=1800, bg="#444", fg="white")
        recalculate()

    ttk.Button(form_btns, text="Zapisz do zamówienia", command=save_to_order).pack(side="left", padx=(0, 8))
    ttk.Button(form_btns, text="Usuń zaznaczoną", command=remove_saved_line).pack(side="left", padx=(0, 8))
    ttk.Button(form_btns, text="Wyczyść zamówienie", command=clear_order).pack(side="left")

    # forward declaration fix — bind after def
    for var in (*vars_map.values(), stripe_var, rounding_var):
        var.trace_add("write", lambda *_a: recalculate())

    root.after(50, recalculate)
    bind_mousewheel_to_canvas(scroll_canvas, inner)
    refresh_scroll()
    return root
