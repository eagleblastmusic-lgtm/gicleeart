"""Widok inline — działalność nierejestrowana (DNR)."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from collections.abc import Callable
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk

from Komponenty._shared.toast import show_toast

from .constants import (
    CEIDG_WARNING,
    DEFAULT_COST_CATEGORIES,
    DEFAULT_QUARTERLY_LIMIT,
    DISCLAIMER,
    DISCOUNT_HINT,
    ELIGIBILITY_ITEMS,
    MONTHLY_GUARDRAIL_HINT,
    MOR_HINT,
    PIT_CASH_HINT,
    PAYMENT_STATUS_LABELS,
    QUARTER_LABELS,
    RECOGNITION_HINT,
    SALE_KIND_LABELS,
    SOURCE_LABELS,
    TAX_CONFIG_ID,
)
from .entry_service import (
    create_cost,
    create_sale,
    delete_costs_many,
    delete_sales_many,
    update_sale,
)
from .export_service import export_year_csv
from .import_policy import shopify_dnr_import_blocked
from .invoice_integration import import_all_for_year, import_invoice, list_importable_invoices
from .shopify_integration import import_all_shopify_for_year, list_importable_shopify_orders
from .models import DnrSettings
from .limit_sync import save_canonical_quarterly_limit
from .storage import get_sale, list_costs, list_sales, load_settings, save_settings
from .summary_service import (
    dashboard_summary,
    limit_status,
    monthly_breakdown,
    pit_cash_revenue_for_year,
    quarterly_breakdown,
    sale_limit_delta,
)
from .migration_service import (
    MIGRATION_STEPS,
    MigrationCompleteError,
    acknowledge_manual_review,
    apply_invoices_jdg_mode,
    apply_kpir_jdg_start,
    complete_migration,
    migration_overview,
    revert_first_exceed,
    set_migration_step,
)
from .kpir_import import import_dnr_to_kpir, preview_dnr_kpir_import

_BG = "#f4f6f9"
_ACCENT = "#5c6bc0"
_LIMIT_COLORS = {
    "ok": "#2e7d32", "caution": "#f9a825", "warn": "#ef6c00",
    "over": "#c62828", "obligation": "#6a1b9a",
}
_MONTH_NAMES = (
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
)


def _append_revert_exceed_row(
    parent: tk.Widget,
    overview: dict[str, Any],
    *,
    bg: str,
    on_success: Callable[[], None],
    dialog_parent: tk.Widget,
) -> None:
    """Przycisk ręcznego cofnięcia zapisanego pierwszego przekroczenia (poniżej limitu)."""
    if not overview.get("can_revert_first_exceed"):
        return
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", pady=(8, 0))
    note_var = tk.StringVar(value="")
    ttk.Entry(row, textvariable=note_var, width=42).pack(side="left", padx=(0, 8))

    def _revert() -> None:
        note = note_var.get().strip()
        fe = (overview.get("migration") or {}).get("first_exceed_date") or "?"
        if not messagebox.askyesno(
            "Cofnij przekroczenie",
            f"Cofnąć zapisane pierwsze przekroczenie ({fe})?\n\n"
            "Użyj tylko gdy po zwrocie/korekcie limit nie został faktycznie przekroczony "
            "(np. błąd wpisu). Przy realnym przekroczeniu obowiązek JDG mógł już powstać — "
            "skonsultuj z księgowym.",
            parent=dialog_parent,
        ):
            return
        try:
            revert_first_exceed(note=note)
            show_toast(dialog_parent, "Cofnięto zapis przekroczenia", bg="#2e7d32")
            on_success()
        except MigrationCompleteError as exc:
            messagebox.showerror("Cofnięcie", str(exc), parent=dialog_parent)

    ttk.Button(
        row,
        text="Cofnij zapisane przekroczenie",
        command=_revert,
    ).pack(side="left")
    tk.Label(
        row,
        text="Uzasadnienie (min. 3 znaki)",
        bg=bg,
        fg="#795548",
        font=("Segoe UI", 8),
    ).pack(side="left", padx=(8, 0))


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    return DnrView(parent, on_back).frame


class DnrView:
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        self.parent = parent
        self.on_back = on_back
        self.frame = tk.Frame(parent, bg=_BG)
        self._screen: tk.Widget | None = None
        self._year = date.today().year
        self._nav_entry_screen: str | None = None
        self._apply_finance_nav()
        if self._screen is None:
            self.show_dashboard()

    def _apply_finance_nav(self) -> None:
        from Komponenty._shared.finance_navigation import consume_nav

        nav = consume_nav("dnr")
        if not nav:
            return
        self._nav_entry_screen = nav.screen
        routes = {
            "import": self.show_import,
            "sales": self.show_sales,
            "migration": self.show_migration_wizard,
            "settings": self.show_settings,
            "month_close": self.show_month_close,
        }
        fn = routes.get(nav.screen)
        if fn:
            fn()

    def _back_for(self, screen: str) -> Callable[[], None]:
        from Komponenty._shared.finance_navigation import back_for_nav_entry

        return back_for_nav_entry(
            entry_screen=self._nav_entry_screen,
            current_screen=screen,
            hub_back=self.on_back,
            module_back=self.show_dashboard,
        )

    def _swap(self, screen: tk.Widget) -> None:
        if self._screen:
            self._screen.destroy()
        self._screen = screen
        screen.pack(fill="both", expand=True)

    def _toolbar(self, parent: tk.Widget, title: str, *, back: Callable[[], None] | None = None) -> tk.Frame:
        bar = tk.Frame(parent, bg=_BG)
        bar.pack(fill="x", padx=12, pady=8)
        tk.Button(bar, text="← Wróć", command=back or self.show_dashboard, bg="#fff").pack(side="left")
        tk.Label(bar, text=title, font=("Segoe UI", 14, "bold"), bg=_BG).pack(side="left", padx=12)
        return bar

    def _nav_buttons(self, parent: tk.Widget) -> None:
        nav = tk.Frame(parent, bg=_BG)
        nav.pack(fill="x", side="bottom", padx=16, pady=(8, 12))
        items = [
            ("Sprzedaż", self.show_sales),
            ("Koszty", self.show_costs),
            ("Podsumowanie", self.show_summary),
            ("Zamknięcie miesiąca", self.show_month_close),
            ("Import", self.show_import),
            ("Eksport CSV", self.show_export),
            ("Ustawienia", self.show_settings),
        ]
        for i, (label, cmd) in enumerate(items):
            tk.Button(
                nav, text=label, command=cmd, bg="#fff", fg="#333",
                font=("Segoe UI", 10), padx=8, pady=4,
            ).grid(row=i // 3, column=i % 3, padx=4, pady=3, sticky="ew")
        for col in range(3):
            nav.grid_columnconfigure(col, weight=1)

    def _draw_limit_bar(self, parent: tk.Widget, status: dict, *, title: str = "") -> tk.Canvas:
        if title:
            tk.Label(
                parent, text=title, bg=_BG, fg="#444",
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", pady=(0, 2))
        canvas = tk.Canvas(parent, height=28, bg="#e0e0e0", highlightthickness=0)
        canvas.pack(fill="x", pady=(0, 8))
        pct = min(100.0, float(status.get("pct") or 0))
        color = _LIMIT_COLORS.get(str(status.get("level")), _ACCENT)
        w = max(parent.winfo_width() or 400, 200)
        rev = float(status.get("quarter_revenue", status.get("limit_revenue", 0)) or 0)
        lim = float(status.get("quarterly_limit", 0) or 0)

        def _paint(evt: object = None) -> None:
            canvas.delete("all")
            width = canvas.winfo_width() or w
            fill_w = int(width * pct / 100)
            canvas.create_rectangle(0, 0, width, 28, fill="#e0e0e0", outline="")
            if fill_w > 0:
                canvas.create_rectangle(0, 0, fill_w, 28, fill=color, outline="")
            canvas.create_text(
                width // 2, 14,
                text=f"{rev:.2f} / {lim:.2f} PLN ({pct}%)",
                fill="#111" if pct < 55 else "#fff",
                font=("Segoe UI", 10, "bold"),
            )

        canvas.bind("<Configure>", _paint)
        parent.after(50, _paint)
        return canvas

    def show_dashboard(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Działalność nierejestrowana", back=self.on_back)
        dash = dashboard_summary(self._year)

        alert = tk.Frame(outer, bg=_BG, padx=16)
        alert.pack(fill="x")
        level = str(dash.get("level") or "ok")
        tk.Label(
            alert,
            text=str(dash.get("message") or ""),
            fg=_LIMIT_COLORS.get(level, "#333"),
            bg=_BG,
            font=("Segoe UI", 11, "bold"),
            wraplength=700,
            justify="left",
        ).pack(anchor="w")
        if not dash.get("eligibility_complete"):
            tk.Label(
                alert,
                text="Uzupełnij checklistę warunków DNR w Ustawieniach przed startem ewidencji.",
                fg="#1565c0",
                bg="#e3f2fd",
                font=("Segoe UI", 9, "bold"),
                wraplength=700,
                justify="left",
                padx=8,
                pady=4,
            ).pack(anchor="w", fill="x", pady=(4, 0))
        mg = dash.get("monthly_guardrail") or {}
        mg_level = str(mg.get("level") or "ok")
        if mg_level != "ok":
            tk.Label(
                alert,
                text=str(mg.get("message") or ""),
                fg=_LIMIT_COLORS.get("caution" if mg_level == "caution" else "warn", "#ef6c00"),
                bg=_BG,
                font=("Segoe UI", 9),
                wraplength=700,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        limit_frame = tk.Frame(outer, bg=_BG, padx=16)
        limit_frame.pack(fill="x")
        self._draw_limit_bar(
            limit_frame, dash,
            title=f"Bieżący {dash.get('quarter_label', 'kwartał')} — przychód należny (limit)",
        )
        tk.Label(
            limit_frame,
            text=RECOGNITION_HINT,
            fg="#555",
            bg=_BG,
            font=("Segoe UI", 8),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))
        tk.Label(
            limit_frame,
            text=PIT_CASH_HINT,
            fg="#555",
            bg=_BG,
            font=("Segoe UI", 8),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        q_frame = tk.Frame(outer, bg=_BG, padx=16, pady=4)
        q_frame.pack(fill="x")
        tk.Label(
            q_frame, text="Kwartały", bg=_BG, font=("Segoe UI", 10, "bold"), fg="#444",
        ).pack(anchor="w", pady=(0, 6))
        quarters_row = tk.Frame(q_frame, bg=_BG)
        quarters_row.pack(fill="x")
        for qrow in dash.get("quarters") or []:
            q = int(qrow["quarter"])
            if qrow.get("over_limit"):
                lvl = "over"
            elif qrow.get("obligation_active"):
                lvl = "obligation"
            else:
                lvl = (
                    "warn" if qrow["pct"] >= 90 else "caution" if qrow["pct"] >= 75 else "ok"
                )
            border = _LIMIT_COLORS.get(lvl, "#ddd")
            highlight = "#1565c0" if q == dash.get("quarter") else border
            card = tk.Frame(
                quarters_row, bg="#fff", padx=10, pady=8,
                highlightbackground=highlight, highlightthickness=2 if q == dash.get("quarter") else 1,
            )
            card.pack(side="left", padx=4, pady=2)
            tk.Label(
                card, text=f"Q{q}", font=("Segoe UI", 9, "bold"), bg="#fff", fg="#666",
            ).pack(anchor="w")
            tk.Label(
                card,
                text=f"{qrow['limit_revenue']:.2f} / {qrow['quarterly_limit']:.2f}",
                font=("Segoe UI", 11, "bold"), bg="#fff", fg=border,
            ).pack(anchor="w")
            sub = (
                "obowiązek JDG — poniżej limitu"
                if qrow.get("obligation_active")
                else f"pozostało {qrow['remaining']:.2f}"
            )
            tk.Label(
                card, text=sub, font=("Segoe UI", 8), bg="#fff", fg=border,
            ).pack(anchor="w")

        cards = tk.Frame(outer, bg=_BG)
        cards.pack(fill="x", padx=16, pady=8)
        metrics = [
            ("Przychód należny (miesiąc)", f"{dash['month_limit_revenue']:.2f} PLN", "#1565c0"),
            ("Koszty (miesiąc)", f"{dash['month_costs']:.2f} PLN", "#6d4c41"),
            ("Przychód należny (kwartał)", f"{dash['quarter_revenue']:.2f} PLN", _ACCENT),
            ("Pozostało w kwartale", f"{dash['remaining']:.2f} PLN", "#00838f"),
            ("Przychód należny (rok)", f"{dash['year_revenue']:.2f} PLN", "#5c6bc0"),
            ("Wpływy kasowe PIT (rok)", f"{dash.get('pit_cash_revenue_year', 0):.2f} PLN", "#2e7d32"),
            ("Wpływy kasowe PIT (kwartał)", f"{dash.get('pit_cash_revenue_quarter', 0):.2f} PLN", "#388e3c"),
            ("Koszty (rok)", f"{dash['year_costs']:.2f} PLN", "#795548"),
        ]
        for i, (title, value, color) in enumerate(metrics):
            card = tk.Frame(cards, bg="#fff", padx=10, pady=8, highlightbackground="#ddd", highlightthickness=1)
            card.grid(row=i // 3, column=i % 3, padx=5, pady=4, sticky="nw")
            tk.Label(card, text=title, font=("Segoe UI", 9), bg="#fff", fg="#666").pack(anchor="w")
            tk.Label(card, text=value, font=("Segoe UI", 12, "bold"), bg="#fff", fg=color).pack(anchor="w")

        tk.Label(
            outer, text=DISCLAIMER, fg="#777", bg=_BG, font=("Segoe UI", 9),
            wraplength=720, justify="left",
        ).pack(anchor="w", padx=16, pady=(4, 0))
        tk.Label(
            outer, text=f"{MONTHLY_GUARDRAIL_HINT} Konfiguracja: {TAX_CONFIG_ID}.",
            fg="#999", bg=_BG, font=("Segoe UI", 8),
            wraplength=720, justify="left",
        ).pack(anchor="w", padx=16, pady=(2, 0))
        if dash.get("over_limit") or dash.get("obligation_active"):
            warn_bg = "#ffebee" if dash.get("over_limit") else "#f3e5f5"
            warn_fg = "#c62828" if dash.get("over_limit") else "#6a1b9a"
            warn_text = (
                CEIDG_WARNING
                if dash.get("over_limit")
                else (
                    f"Obowiązek JDG od {dash.get('first_exceed_date', '?')} — "
                    "ewidencja jest poniżej limitu, ale rejestracja mogła powstać od dnia przekroczenia."
                )
            )
            tk.Label(
                outer, text=warn_text, fg=warn_fg, bg=warn_bg, font=("Segoe UI", 9, "bold"),
                wraplength=720, justify="left", padx=8, pady=6,
            ).pack(anchor="w", padx=16, pady=(6, 0), fill="x")

        mig = migration_overview()
        if mig.get("manual_review_alert"):
            mr_box = tk.Frame(outer, bg="#fff8e1", padx=12, pady=8)
            mr_box.pack(fill="x", padx=16, pady=(8, 0))
            tk.Label(
                mr_box,
                text="⚠ Wymaga ręcznej weryfikacji (przypadek brzegowy limitu DNR)",
                fg="#e65100",
                bg="#fff8e1",
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w")
            for reason in mig.get("manual_review_reasons") or [mig.get("manual_review_message", "")]:
                if reason:
                    tk.Label(
                        mr_box,
                        text=str(reason),
                        fg="#5d4037",
                        bg="#fff8e1",
                        font=("Segoe UI", 9),
                        wraplength=680,
                        justify="left",
                    ).pack(anchor="w", pady=(2, 0))
            if mig.get("migration", {}).get("first_exceed_date"):
                fe = mig["migration"]
                tk.Label(
                    mr_box,
                    text=(
                        f"Zapisane pierwsze przekroczenie: {fe.get('first_exceed_date')} "
                        f"(Q{fe.get('first_exceed_quarter')}, +{fe.get('first_exceed_excess_pln', 0):.2f} zł)."
                    ),
                    fg="#795548",
                    bg="#fff8e1",
                    font=("Segoe UI", 8),
                    wraplength=680,
                    justify="left",
                ).pack(anchor="w", pady=(4, 0))
            _append_revert_exceed_row(
                mr_box,
                mig,
                bg="#fff8e1",
                on_success=self.show_dashboard,
                dialog_parent=outer,
            )
        elif mig.get("can_revert_first_exceed"):
            rev_box = tk.Frame(outer, bg="#f5f5f5", padx=12, pady=8)
            rev_box.pack(fill="x", padx=16, pady=(8, 0))
            tk.Label(
                rev_box,
                text=(
                    "Ewidencja poniżej limitu, ale zapisano pierwsze przekroczenie. "
                    "Jeśli to był błąd lub zwrot cofnął realne przekroczenie — możesz ręcznie usunąć zapis."
                ),
                fg="#555",
                bg="#f5f5f5",
                font=("Segoe UI", 9),
                wraplength=680,
                justify="left",
            ).pack(anchor="w")
            _append_revert_exceed_row(
                rev_box,
                mig,
                bg="#f5f5f5",
                on_success=self.show_dashboard,
                dialog_parent=outer,
            )

        if mig.get("wizard_needed"):
            mig_level = str(mig.get("level") or "warn")
            mig_bg = {"over": "#ffebee", "warn": "#fff3e0", "caution": "#fff8e1"}.get(mig_level, "#e3f2fd")
            mig_fg = _LIMIT_COLORS.get(mig_level, "#1565c0")
            mig_box = tk.Frame(outer, bg=mig_bg, padx=12, pady=8)
            mig_box.pack(fill="x", padx=16, pady=(8, 0))
            tk.Label(
                mig_box,
                text=str(mig.get("message") or "Wymagana migracja DNR → JDG."),
                fg=mig_fg,
                bg=mig_bg,
                font=("Segoe UI", 10, "bold"),
                wraplength=680,
                justify="left",
            ).pack(anchor="w")
            tk.Button(
                mig_box,
                text="Kreator przejścia DNR → JDG",
                command=self.show_migration_wizard,
                bg="#5c6bc0",
                fg="#fff",
                font=("Segoe UI", 10, "bold"),
                padx=12,
                pady=4,
            ).pack(anchor="w", pady=(6, 0))

        self._nav_buttons(outer)
        self._swap(outer)

    def show_migration_wizard(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Kreator DNR → JDG", back=self._back_for("migration"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        overview = migration_overview()
        mig = overview.get("migration") or {}
        event = overview.get("exceed_event") or {}
        level = str(overview.get("level") or "ok")
        tk.Label(
            body,
            text=str(overview.get("message") or ""),
            fg=_LIMIT_COLORS.get(level, "#333"),
            bg=_BG,
            font=("Segoe UI", 11, "bold"),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        if overview.get("manual_review_alert"):
            review_box = tk.Frame(body, bg="#fff8e1", padx=10, pady=8)
            review_box.pack(fill="x", pady=(0, 8))
            tk.Label(
                review_box,
                text="Weryfikacja ręczna — korekta w ewidencji nie cofa obowiązku JDG",
                fg="#e65100",
                bg="#fff8e1",
                font=("Segoe UI", 10, "bold"),
                wraplength=660,
                justify="left",
            ).pack(anchor="w")
            for reason in overview.get("manual_review_reasons") or []:
                tk.Label(
                    review_box,
                    text=f"• {reason}",
                    fg="#5d4037",
                    bg="#fff8e1",
                    font=("Segoe UI", 9),
                    wraplength=660,
                    justify="left",
                ).pack(anchor="w", pady=(2, 0))
            ack_row = tk.Frame(review_box, bg="#fff8e1")
            ack_row.pack(fill="x", pady=(8, 0))
            ack_note = tk.StringVar(value="")
            ttk.Entry(ack_row, textvariable=ack_note, width=48).pack(side="left", padx=(0, 8))

            def _ack_review() -> None:
                try:
                    acknowledge_manual_review(note=ack_note.get())
                    show_toast(outer, "Weryfikacja potwierdzona", bg="#2e7d32")
                    self.show_migration_wizard()
                except MigrationCompleteError as exc:
                    messagebox.showerror("Weryfikacja", str(exc), parent=outer)

            ttk.Button(ack_row, text="Potwierdzam weryfikację", command=_ack_review).pack(side="left")
            _append_revert_exceed_row(
                review_box,
                overview,
                bg="#fff8e1",
                on_success=self.show_migration_wizard,
                dialog_parent=outer,
            )
        elif mig.get("manual_review_acknowledged"):
            tk.Label(
                body,
                text=f"Weryfikacja ręczna potwierdzona ({mig.get('manual_review_ack_at', '?')}).",
                fg="#2e7d32",
                bg=_BG,
                font=("Segoe UI", 9),
                wraplength=700,
                justify="left",
            ).pack(anchor="w", pady=(0, 8))
        if overview.get("can_revert_first_exceed") and not overview.get("manual_review_alert"):
            rev_box = tk.Frame(body, bg="#f5f5f5", padx=10, pady=8)
            rev_box.pack(fill="x", pady=(0, 8))
            tk.Label(
                rev_box,
                text="Cofnięcie zapisanego przekroczenia (ewidencja już poniżej limitu):",
                fg="#555",
                bg="#f5f5f5",
                font=("Segoe UI", 9),
                wraplength=660,
                justify="left",
            ).pack(anchor="w")
            _append_revert_exceed_row(
                rev_box,
                overview,
                bg="#f5f5f5",
                on_success=self.show_migration_wizard,
                dialog_parent=outer,
            )
        if event:
            tk.Label(
                body,
                text=(
                    f"Przekroczenie w {event.get('quarter_label', '?')}: "
                    f"{event.get('cumulative_pln', 0):.2f} PLN "
                    f"(nadwyżka {event.get('excess_pln', 0):.2f} PLN). "
                    f"Data skutku: {mig.get('effective_date', '?')}. "
                    f"Termin CEIDG: {mig.get('ceidg_deadline', '?')}."
                ),
                fg="#555",
                bg=_BG,
                font=("Segoe UI", 9),
                wraplength=700,
                justify="left",
            ).pack(anchor="w", pady=(0, 12))
        elif mig.get("first_exceed_date"):
            tk.Label(
                body,
                text=(
                    f"Pierwsze przekroczenie (zapisane): {mig.get('first_exceed_date')} — "
                    f"+{mig.get('first_exceed_excess_pln', 0):.2f} zł, "
                    f"CEIDG do {mig.get('first_exceed_ceidg_deadline') or mig.get('ceidg_deadline', '?')}."
                ),
                fg="#555",
                bg=_BG,
                font=("Segoe UI", 9),
                wraplength=700,
                justify="left",
            ).pack(anchor="w", pady=(0, 12))

        steps_frame = ttk.LabelFrame(body, text=" Checklista migracji ", padding=10)
        steps_frame.pack(fill="x", pady=(0, 12))
        step_vars: dict[str, tk.BooleanVar] = {}
        steps_done = mig.get("steps") or {}

        def _toggle_step(key: str) -> None:
            try:
                set_migration_step(key, done=step_vars[key].get())
            except MigrationCompleteError as exc:
                step_vars[key].set(False)
                messagebox.showerror("Migracja", str(exc), parent=outer)
                return
            show_toast(outer, "Krok zapisany", bg="#2e7d32")

        for key, label in MIGRATION_STEPS:
            row = tk.Frame(steps_frame, bg="#fff")
            row.pack(fill="x", pady=3)
            var = tk.BooleanVar(value=bool(steps_done.get(key)))
            step_vars[key] = var
            ttk.Checkbutton(row, text=label, variable=var, command=lambda k=key: _toggle_step(k)).pack(
                side="left", anchor="w",
            )

        import_box = ttk.LabelFrame(body, text=" Import DNR → KPiR ", padding=10)
        import_box.pack(fill="x", pady=(0, 12))
        imp = overview.get("dnr_import_preview") or {}
        until_d = imp.get("until_date") or "?"
        tk.Label(
            import_box,
            text=(
                f"Okres DNR do daty rejestracji JDG: {until_d}. "
                f"Do importu: {imp.get('to_import', 0)}, "
                f"do powiązania z fakturą: {imp.get('to_link', 0)}, "
                f"pominięte: {imp.get('skipped', 0)}."
            ),
            fg="#444",
            bg="#fff",
            font=("Segoe UI", 9),
            wraplength=660,
            justify="left",
        ).pack(anchor="w")

        def _preview_import() -> None:
            preview = preview_dnr_kpir_import()
            lines = [
                f"Data końca okresu DNR: {preview.until_date}",
                f"Import: {preview.to_import}, powiązanie: {preview.to_link}, pominięte: {preview.skipped}",
                "",
            ]
            for row in preview.rows[:40]:
                lines.append(
                    f"• [{row.kind}] {row.event_date} {row.amount_pln:+.2f} zł — {row.action}: {row.description}"
                )
            if len(preview.rows) > 40:
                lines.append(f"... i {len(preview.rows) - 40} kolejnych wpisów")
            messagebox.showinfo("Podgląd importu DNR → KPiR", "\n".join(lines), parent=outer)

        def _run_import() -> None:
            preview = preview_dnr_kpir_import()
            if preview.actionable == 0:
                messagebox.showinfo(
                    "Import DNR → KPiR",
                    "Brak wpisów do importu — wszystkie są już przeniesione, powiązane lub poza okresem DNR.",
                    parent=outer,
                )
                step_vars["dnr_imported"].set(True)
                return
            if not messagebox.askyesno(
                "Import DNR → KPiR",
                f"Przenieść {preview.to_import} wpisów do KPiR "
                f"i powiązać {preview.to_link} z istniejącymi?\n\n"
                f"Wpisy zostaną oznaczone w DNR jako zamknięte (nie wliczane do limitu/VAT).",
                parent=outer,
            ):
                return
            result = import_dnr_to_kpir()
            msg = (
                f"Zaimportowano sprzedaży: {result.imported_sales}, kosztów: {result.imported_costs}, "
                f"powiązano: {result.linked_sales}, pominięto: {result.skipped}."
            )
            if result.errors:
                msg += "\n\nBłędy:\n" + "\n".join(result.errors[:8])
            messagebox.showinfo("Import DNR → KPiR", msg, parent=outer)
            if not result.errors:
                step_vars["dnr_imported"].set(True)
                show_toast(outer, "Import DNR zakończony", bg="#2e7d32")
            self.show_migration_wizard()

        imp_row = tk.Frame(import_box, bg="#fff")
        imp_row.pack(fill="x", pady=(8, 0))
        ttk.Button(imp_row, text="Podgląd importu", command=_preview_import).pack(side="left", padx=(0, 8))
        ttk.Button(imp_row, text="3. Importuj okres DNR do KPiR", command=_run_import).pack(side="left")

        actions = ttk.LabelFrame(body, text=" Akcje w aplikacji ", padding=10)
        actions.pack(fill="x", pady=(0, 12))

        def _switch_invoices() -> None:
            footnote = apply_invoices_jdg_mode()
            step_vars["invoices_switched"].set(True)
            messagebox.showinfo(
                "Faktury",
                "Tryb sprzedawcy ustawiony na JDG (zwolnienie z VAT).\n\n"
                f"Stopka faktury:\n{footnote}",
                parent=outer,
            )
            show_toast(outer, "Faktury przełączone na JDG", bg="#2e7d32")

        def _enable_kpir() -> None:
            result = apply_kpir_jdg_start(owner_name=load_settings().owner_name)
            step_vars["kpir_enabled"].set(True)
            step_vars["zus_configured"].set(True)
            messagebox.showinfo(
                "KPiR",
                "Włączono KPiR (JDG — KPiR), skala podatkowa, ulga na start ZUS.\n\n"
                f"Data rejestracji JDG: {result.get('jdg_registered_at', '?')}\n"
                f"Etap ZUS: {result.get('zus_stage', 'ulga_na_start')}",
                parent=outer,
            )
            show_toast(outer, "KPiR i ZUS skonfigurowane", bg="#2e7d32")

        def _finish() -> None:
            try:
                complete_migration()
            except MigrationCompleteError as exc:
                messagebox.showerror("Migracja", str(exc), parent=outer)
                return
            show_toast(outer, "Migracja zakończona", bg="#2e7d32")
            self.show_dashboard()

        ttk.Button(
            actions,
            text="1. Przełącz faktury na JDG (zwolnienie z VAT)",
            command=_switch_invoices,
        ).pack(anchor="w", pady=2)
        ttk.Button(
            actions,
            text="2. Włącz KPiR + ulga na start ZUS (pierwszy miesiąc)",
            command=_enable_kpir,
        ).pack(anchor="w", pady=2)
        tk.Label(
            actions,
            text="CEIDG złóż samodzielnie na ceidg.gov.pl — zaznacz krok po złożeniu wniosku.",
            fg="#666",
            bg=_BG,
            font=("Segoe UI", 9),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

        btn_row = tk.Frame(body, bg=_BG)
        btn_row.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_row, text="Oznacz migrację jako zakończoną", command=_finish).pack(side="left")
        ttk.Button(btn_row, text="Odśwież", command=self.show_migration_wizard).pack(side="left", padx=8)

        self._swap(outer)

    def show_sales(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Sprzedaż", back=self._back_for("sales"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        body.pack(fill="both", expand=True)

        pay_order = ("unpaid", "paid", "partial")
        pay_labels = [PAYMENT_STATUS_LABELS[k] for k in pay_order]
        pay_by_label = {v: k for k, v in PAYMENT_STATUS_LABELS.items()}

        form = ttk.LabelFrame(body, text="Wpis przychodu", padding=10)
        form.pack(fill="x")
        kind_order = ("sale", "refund", "correction", "bonification")
        kind_labels = [SALE_KIND_LABELS[k] for k in kind_order]
        fields: dict[str, tk.StringVar] = {
            "event_date": tk.StringVar(value=date.today().isoformat()),
            "entry_kind": tk.StringVar(value=SALE_KIND_LABELS["sale"]),
            "source": tk.StringVar(value=SOURCE_LABELS["manual"]),
            "list_price_pln": tk.StringVar(value=""),
            "discount_pln": tk.StringVar(value=""),
            "amount_pln": tk.StringVar(value="0"),
            "description": tk.StringVar(),
            "document_number": tk.StringVar(),
            "payment_status": tk.StringVar(value=PAYMENT_STATUS_LABELS["paid"]),
            "paid_at": tk.StringVar(value=""),
            "amount_received_pln": tk.StringVar(value=""),
        }
        mor_var = tk.BooleanVar(value=False)
        edit_id: dict[str, str | None] = {"id": None}
        mode_var = tk.StringVar(value="Nowy wpis")
        source_labels = list(SOURCE_LABELS.values())
        source_by_label = {v: k for k, v in SOURCE_LABELS.items()}

        mode_row = tk.Frame(form)
        mode_row.pack(fill="x", pady=(0, 4))
        ttk.Label(mode_row, textvariable=mode_var, font=("Segoe UI", 9, "bold")).pack(side="left")

        row1 = tk.Frame(form)
        row1.pack(fill="x", pady=2)
        for lbl, key, w in [
            ("Data", "event_date", 12), ("Rodzaj", "entry_kind", 18),
            ("Źródło", "source", 12), ("Dokument", "document_number", 14),
        ]:
            ttk.Label(row1, text=lbl).pack(side="left", padx=(0, 2))
            if key == "entry_kind":
                ttk.Combobox(
                    row1, textvariable=fields[key], values=kind_labels, width=w, state="readonly",
                ).pack(side="left", padx=(0, 8))
            elif key == "source":
                ttk.Combobox(
                    row1, textvariable=fields[key], values=source_labels, width=w, state="readonly",
                ).pack(side="left", padx=(0, 8))
            else:
                ttk.Entry(row1, textvariable=fields[key], width=w).pack(side="left", padx=(0, 8))

        row2 = tk.Frame(form)
        row2.pack(fill="x", pady=2)
        for lbl, key, w in [
            ("Cena (opcj.)", "list_price_pln", 10),
            ("Rabat (opcj.)", "discount_pln", 10),
            ("Przychód należny", "amount_pln", 10),
            ("Opis", "description", 28),
        ]:
            ttk.Label(row2, text=lbl).pack(side="left", padx=(0, 2))
            ttk.Entry(row2, textvariable=fields[key], width=w).pack(side="left", padx=(0, 8))

        row3 = tk.Frame(form)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="Płatność").pack(side="left", padx=(0, 2))
        ttk.Combobox(
            row3, textvariable=fields["payment_status"], values=pay_labels, width=14, state="readonly",
        ).pack(side="left", padx=(0, 8))
        ttk.Label(row3, text="Data wpływu").pack(side="left", padx=(0, 2))
        ttk.Entry(row3, textvariable=fields["paid_at"], width=12).pack(side="left", padx=(0, 8))
        ttk.Label(row3, text="Kwota wpływu").pack(side="left", padx=(0, 2))
        ttk.Entry(row3, textvariable=fields["amount_received_pln"], width=10).pack(side="left", padx=(0, 8))

        def _sync_net(*_: object) -> None:
            try:
                lp = float(str(fields["list_price_pln"].get()).replace(",", ".") or 0)
                disc = float(str(fields["discount_pln"].get()).replace(",", ".") or 0)
                if lp > 0:
                    fields["amount_pln"].set(f"{max(0.0, lp - disc):.2f}")
            except ValueError:
                pass

        def _sync_received(*_: object) -> None:
            pay = pay_by_label.get(fields["payment_status"].get(), "paid")
            if pay == "paid" and not fields["amount_received_pln"].get().strip():
                try:
                    fields["amount_received_pln"].set(fields["amount_pln"].get())
                except Exception:
                    pass
            if pay == "unpaid":
                fields["amount_received_pln"].set("0")

        fields["list_price_pln"].trace_add("write", _sync_net)
        fields["discount_pln"].trace_add("write", _sync_net)
        fields["payment_status"].trace_add("write", _sync_received)
        fields["amount_pln"].trace_add("write", _sync_received)

        def _on_source_change(*_: object) -> None:
            src = source_by_label.get(fields["source"].get(), "manual")
            if src == "allegro":
                from Komponenty._shared.tax_config import merchant_of_record_default
                mor_var.set(merchant_of_record_default("allegro"))
            elif mor_var.get():
                mor_var.set(False)

        fields["source"].trace_add("write", _on_source_change)
        mor_row = tk.Frame(form)
        mor_row.pack(fill="x", pady=2)
        ttk.Checkbutton(
            mor_row, text="Merchant of record (platforma sprzedawcą — poza limitem DNR/VAT)", variable=mor_var,
        ).pack(side="left")
        tk.Label(mor_row, text=MOR_HINT, fg="#666", font=("Segoe UI", 8)).pack(side="left", padx=(8, 0))

        tk.Label(
            form, text=DISCOUNT_HINT, bg=_BG, fg="#666", font=("Segoe UI", 9),
            wraplength=680, justify="left",
        ).pack(anchor="w", pady=(4, 0))
        tk.Label(
            form, text=PIT_CASH_HINT, bg=_BG, fg="#666", font=("Segoe UI", 8),
            wraplength=680, justify="left",
        ).pack(anchor="w", pady=(2, 0))

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True, pady=8)
        cols = ("date", "kind", "cena", "rabat", "nalezny", "pay", "wpływ", "kasowy", "limit", "desc", "src")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14, selectmode="extended")
        for cid, txt, w in [
            ("date", "Data", 85), ("kind", "Rodzaj", 75), ("cena", "Cena", 60), ("rabat", "Rabat", 60),
            ("nalezny", "Należny", 65), ("pay", "Płatność", 75), ("wpływ", "Data wpływu", 85),
            ("kasowy", "Kasowy", 65), ("limit", "Limit", 60), ("desc", "Opis", 140), ("src", "Źródło", 65),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        id_map: dict[str, str] = {}

        def _clear_form() -> None:
            edit_id["id"] = None
            mode_var.set("Nowy wpis")
            fields["event_date"].set(date.today().isoformat())
            fields["entry_kind"].set(SALE_KIND_LABELS["sale"])
            fields["source"].set(SOURCE_LABELS["manual"])
            fields["list_price_pln"].set("")
            fields["discount_pln"].set("")
            fields["amount_pln"].set("0")
            fields["description"].set("")
            fields["document_number"].set("")
            fields["payment_status"].set(PAYMENT_STATUS_LABELS["paid"])
            fields["paid_at"].set("")
            fields["amount_received_pln"].set("")
            mor_var.set(False)

        def refresh() -> None:
            id_map.clear()
            for i in tree.get_children():
                tree.delete(i)
            for s in sorted(list_sales(), key=lambda x: x.event_date, reverse=True):
                if not s.event_date.startswith(f"{self._year:04d}"):
                    continue
                pay_lbl = PAYMENT_STATUS_LABELS.get(s.payment_status or "paid", s.payment_status)
                paid_d = (s.paid_at or "")[:10]
                iid = tree.insert("", "end", values=(
                    s.event_date,
                    SALE_KIND_LABELS.get(s.entry_kind or "sale", s.entry_kind),
                    f"{s.list_price_pln:.2f}" if s.list_price_pln else "",
                    f"{s.discount_pln:.2f}" if s.discount_pln else "",
                    f"{s.amount_pln:.2f}",
                    pay_lbl,
                    paid_d,
                    f"{s.amount_received_pln:.2f}",
                    f"{sale_limit_delta(s):+.2f}",
                    s.description,
                    SOURCE_LABELS.get(s.source, s.source),
                ))
                id_map[iid] = s.id

        def _collect_payment() -> tuple[str, str, str]:
            pay = pay_by_label.get(fields["payment_status"].get(), "paid")
            paid_at = fields["paid_at"].get().strip()
            if paid_at and len(paid_at) == 10:
                paid_at = paid_at + "T12:00:00"
            received = fields["amount_received_pln"].get().strip()
            if not received and pay == "paid":
                received = fields["amount_pln"].get()
            return pay, paid_at, received

        def save_sale() -> None:
            try:
                amt = float(str(fields["amount_pln"].get()).replace(",", "."))
            except ValueError:
                messagebox.showerror("DNR", "Nieprawidłowy przychód należny.", parent=outer)
                return
            if amt <= 0:
                messagebox.showwarning("DNR", "Przychód należny musi być większy od zera.", parent=outer)
                return
            label = fields["entry_kind"].get()
            kind = kind_order[kind_labels.index(label)] if label in kind_labels else "sale"
            src = source_by_label.get(fields["source"].get(), "manual")
            pay, paid_at, received = _collect_payment()
            try:
                if edit_id["id"]:
                    update_sale(
                        edit_id["id"],
                        event_date=fields["event_date"].get(),
                        amount_pln=amt,
                        list_price_pln=fields["list_price_pln"].get(),
                        discount_pln=fields["discount_pln"].get(),
                        description=fields["description"].get(),
                        document_number=fields["document_number"].get(),
                        entry_kind=kind,
                        merchant_of_record=mor_var.get(),
                        payment_status=pay,
                        paid_at=paid_at,
                        amount_received_pln=received,
                    )
                    show_toast(outer, "Zapisano zmiany.", bg="#1565c0")
                else:
                    create_sale(
                        event_date=fields["event_date"].get(),
                        amount_pln=amt,
                        list_price_pln=fields["list_price_pln"].get(),
                        discount_pln=fields["discount_pln"].get(),
                        description=fields["description"].get(),
                        document_number=fields["document_number"].get(),
                        entry_kind=kind,
                        source=src,
                        merchant_of_record=mor_var.get(),
                        payment_status=pay,
                        paid_at=paid_at,
                        amount_received_pln=received,
                    )
                    show_toast(outer, f"Dodano: {label}.")
            except ValueError as exc:
                messagebox.showerror("DNR", str(exc), parent=outer)
                return
            _clear_form()
            refresh()

        def load_selected() -> None:
            sel = tree.selection()
            if not sel or sel[0] not in id_map:
                return
            entry = get_sale(id_map[sel[0]])
            if not entry:
                return
            edit_id["id"] = entry.id
            mode_var.set(f"Edycja wpisu ({entry.document_number or entry.id[:8]})")
            fields["event_date"].set(entry.event_date)
            fields["entry_kind"].set(SALE_KIND_LABELS.get(entry.entry_kind or "sale", "sprzedaż"))
            fields["source"].set(SOURCE_LABELS.get(entry.source, entry.source))
            fields["list_price_pln"].set(f"{entry.list_price_pln:.2f}" if entry.list_price_pln else "")
            fields["discount_pln"].set(f"{entry.discount_pln:.2f}" if entry.discount_pln else "")
            fields["amount_pln"].set(f"{entry.amount_pln:.2f}")
            fields["description"].set(entry.description)
            fields["document_number"].set(entry.document_number)
            fields["payment_status"].set(PAYMENT_STATUS_LABELS.get(entry.payment_status or "paid", "opłacone"))
            fields["paid_at"].set((entry.paid_at or "")[:10])
            fields["amount_received_pln"].set(f"{entry.amount_received_pln:.2f}")
            mor_var.set(bool(entry.merchant_of_record))

        def delete_selected() -> None:
            ids = [id_map[i] for i in tree.selection() if i in id_map]
            if not ids:
                return
            if not messagebox.askyesno("DNR", f"Usunąć {len(ids)} wpis(ów)?", parent=outer):
                return
            delete_sales_many(ids)
            if edit_id["id"] in ids:
                _clear_form()
            refresh()
            show_toast(outer, f"Usunięto {len(ids)} wpis(ów).")

        btn_row = tk.Frame(form, bg=_BG)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="Zapisz", command=save_sale).pack(side="left")
        ttk.Button(btn_row, text="Anuluj edycję", command=_clear_form).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Edytuj zaznaczone", command=load_selected).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Usuń zaznaczone", command=delete_selected).pack(side="left", padx=8)
        tree.bind("<Double-1>", lambda _e: load_selected())
        refresh()
        self._swap(outer)

    def show_costs(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Koszty", back=self._back_for("costs"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        body.pack(fill="both", expand=True)

        form = ttk.LabelFrame(body, text="Nowy koszt", padding=10)
        form.pack(fill="x")
        fields: dict[str, tk.StringVar] = {
            "event_date": tk.StringVar(value=date.today().isoformat()),
            "amount_pln": tk.StringVar(value="0"),
            "category": tk.StringVar(value="inne"),
            "seller": tk.StringVar(),
            "description": tk.StringVar(),
            "document_number": tk.StringVar(),
        }
        row1 = tk.Frame(form)
        row1.pack(fill="x", pady=2)
        for lbl, key, w in [
            ("Data", "event_date", 12), ("Kwota PLN", "amount_pln", 10),
            ("Kategoria", "category", 14), ("Sprzedawca", "seller", 18),
        ]:
            ttk.Label(row1, text=lbl).pack(side="left", padx=(0, 2))
            if key == "category":
                ttk.Combobox(row1, textvariable=fields[key], values=DEFAULT_COST_CATEGORIES, width=w).pack(
                    side="left", padx=(0, 8),
                )
            else:
                ttk.Entry(row1, textvariable=fields[key], width=w).pack(side="left", padx=(0, 8))
        row2 = tk.Frame(form)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Dokument").pack(side="left")
        ttk.Entry(row2, textvariable=fields["document_number"], width=14).pack(side="left", padx=4)
        ttk.Label(row2, text="Opis").pack(side="left", padx=(8, 0))
        ttk.Entry(row2, textvariable=fields["description"], width=40).pack(side="left", padx=4)

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True, pady=8)
        cols = ("date", "doc", "seller", "cat", "pln", "desc")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14, selectmode="extended")
        for cid, txt, w in [
            ("date", "Data", 95), ("doc", "Dokument", 100), ("seller", "Sprzedawca", 130),
            ("cat", "Kategoria", 100), ("pln", "PLN", 80), ("desc", "Opis", 200),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        id_map: dict[str, str] = {}

        def refresh() -> None:
            id_map.clear()
            for i in tree.get_children():
                tree.delete(i)
            for c in sorted(list_costs(), key=lambda x: x.event_date, reverse=True):
                if not c.event_date.startswith(f"{self._year:04d}"):
                    continue
                iid = tree.insert("", "end", values=(
                    c.event_date, c.document_number, c.seller, c.category,
                    f"{c.amount_pln:.2f}", c.description,
                ))
                id_map[iid] = c.id

        def add_cost() -> None:
            try:
                amt = float(str(fields["amount_pln"].get()).replace(",", "."))
            except ValueError:
                messagebox.showerror("DNR", "Nieprawidłowa kwota.", parent=outer)
                return
            if amt <= 0:
                messagebox.showwarning("DNR", "Kwota musi być większa od zera.", parent=outer)
                return
            create_cost(
                event_date=fields["event_date"].get(),
                amount_pln=amt,
                category=fields["category"].get(),
                seller=fields["seller"].get(),
                description=fields["description"].get(),
                document_number=fields["document_number"].get(),
            )
            fields["amount_pln"].set("0")
            fields["description"].set("")
            fields["document_number"].set("")
            fields["seller"].set("")
            refresh()
            show_toast(outer, "Dodano koszt.")

        def delete_selected() -> None:
            ids = [id_map[i] for i in tree.selection() if i in id_map]
            if not ids:
                return
            if not messagebox.askyesno("DNR", f"Usunąć {len(ids)} koszt(ów)?", parent=outer):
                return
            delete_costs_many(ids)
            refresh()
            show_toast(outer, f"Usunięto {len(ids)} koszt(ów).")

        btn_row = tk.Frame(form, bg=_BG)
        btn_row.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_row, text="Dodaj", command=add_cost).pack(side="left")
        ttk.Button(btn_row, text="Usuń zaznaczone", command=delete_selected).pack(side="left", padx=8)
        refresh()
        self._swap(outer)

    def show_summary(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Podsumowanie", back=self._back_for("summary"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        body.pack(fill="both", expand=True)

        year_var = tk.StringVar(value=str(self._year))
        top = tk.Frame(body, bg=_BG)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Rok").pack(side="left")
        year_entry = ttk.Entry(top, textvariable=year_var, width=6)
        year_entry.pack(side="left", padx=4)

        comp_box = tk.Frame(body, bg="#f5f5f5", padx=8, pady=6)
        comp_box.pack(fill="x", pady=(0, 8))

        pit_lbl = tk.Label(
            body,
            text="",
            bg=_BG,
            font=("Segoe UI", 10),
            fg="#2e7d32",
            wraplength=700,
            justify="left",
        )
        pit_lbl.pack(anchor="w", pady=(0, 6))

        q_frame = ttk.LabelFrame(body, text="Kwartały — limit przychodu należnego", padding=8)
        q_frame.pack(fill="x", pady=(0, 8))
        q_cols = ("q", "rev", "adj", "limit", "rem", "pct")
        q_tree = ttk.Treeview(q_frame, columns=q_cols, show="headings", height=4)
        for cid, txt, w in [
            ("q", "Kwartał", 150), ("rev", "Przychód należny", 110), ("adj", "Zwroty/korekty", 100),
            ("limit", "Limit", 90), ("rem", "Pozostało", 90), ("pct", "%", 50),
        ]:
            q_tree.heading(cid, text=txt)
            q_tree.column(cid, width=w)
        q_tree.pack(fill="x")

        m_frame = ttk.LabelFrame(body, text="Miesiące", padding=8)
        m_frame.pack(fill="both", expand=True)
        cols = ("month", "q", "rev", "cost", "profit", "sales", "costs_n")
        tree = ttk.Treeview(m_frame, columns=cols, show="headings", height=10)
        for cid, txt, w in [
            ("month", "Miesiąc", 100), ("q", "Kw.", 40), ("rev", "Przychód należny", 100),
            ("cost", "Koszty", 80), ("profit", "Wynik", 80),
            ("sales", "Wpisy", 55), ("costs_n", "Kosztów", 55),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True)
        total_lbl = tk.Label(body, text="", bg=_BG, font=("Segoe UI", 11, "bold"), wraplength=700, justify="left")
        total_lbl.pack(anchor="w", pady=8)

        def refresh() -> None:
            try:
                y = int(year_var.get())
            except ValueError:
                y = self._year
            self._year = y
            for i in q_tree.get_children():
                q_tree.delete(i)
            for row in quarterly_breakdown(y):
                q = row["quarter"]
                q_tree.insert("", "end", values=(
                    QUARTER_LABELS[q],
                    f"{row['limit_revenue']:.2f}",
                    f"{row['adjustments']:.2f}",
                    f"{row['quarterly_limit']:.2f}",
                    f"{row['remaining']:.2f}",
                    f"{row['pct']:.0f}%",
                ))
            for i in tree.get_children():
                tree.delete(i)
            rows = monthly_breakdown(y)
            for row in rows:
                m = row["month"]
                tree.insert("", "end", values=(
                    _MONTH_NAMES[m - 1],
                    f"Q{row['quarter']}",
                    f"{row['revenue']:.2f}",
                    f"{row['costs']:.2f}",
                    f"{row['profit']:.2f}",
                    row["sale_count"],
                    row["cost_count"],
                ))
            lim = limit_status(y)
            pit_y = pit_cash_revenue_for_year(y)
            pit_lbl.config(
                text=(
                    f"Wpływy kasowe do PIT-36 (inne źródła), rok {y}: {pit_y:.2f} PLN. "
                    f"{PIT_CASH_HINT}"
                ),
            )
            for w in comp_box.winfo_children():
                w.destroy()
            try:
                from Komponenty._shared.compliance_monitors import (
                    foreign_service_alerts,
                    ksef_b2b_monthly_status,
                    wsto_oss_status,
                )
                for title, st in (
                    ("WSTO / OSS", wsto_oss_status(y)),
                    ("KSeF B2B (mies.)", ksef_b2b_monthly_status(y)),
                    ("Art. 28b / VAT-UE", foreign_service_alerts(year=y)),
                ):
                    tk.Label(
                        comp_box,
                        text=f"{title}: {st.get('message', '')}",
                        bg="#f5f5f5",
                        fg="#333",
                        font=("Segoe UI", 9),
                        wraplength=680,
                        justify="left",
                    ).pack(anchor="w", pady=1)
            except ImportError:
                tk.Label(comp_box, text="Monitory compliance niedostępne.", bg="#f5f5f5").pack(anchor="w")
            except Exception as exc:
                tk.Label(
                    comp_box,
                    text=f"Monitory compliance: {exc}",
                    bg="#f5f5f5",
                    fg="#c62828",
                    wraplength=680,
                    justify="left",
                ).pack(anchor="w")
            total_lbl.config(
                text=(
                    f"Rok {y}: przychód należny {lim['year_revenue']:.2f} PLN, "
                    f"koszty {lim['year_costs']:.2f} PLN — {lim['message']}"
                ),
                fg=_LIMIT_COLORS.get(str(lim.get("level")), "#333"),
            )

        ttk.Button(top, text="Odśwież", command=refresh).pack(side="left", padx=8)
        refresh()
        self._swap(outer)

    def show_import(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Import do DNR", back=self._back_for("import"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        body.pack(fill="both", expand=True)

        inv_frame = ttk.LabelFrame(body, text=" Faktury (Dokumenty sprzedaży) ", padding=8)
        inv_frame.pack(fill="both", expand=True, pady=(0, 8))
        tk.Label(
            inv_frame,
            text=(
                "Wystawione faktury z GicleeApp („Dokumenty sprzedaży”) — Shopify nie generuje faktur; "
                "to jest zalecana ścieżka do DNR."
            ),
            bg=_BG, fg="#555", font=("Segoe UI", 9), wraplength=720, justify="left",
        ).pack(anchor="w", pady=(0, 6))

        tree_frame = ttk.Frame(inv_frame)
        tree_frame.pack(fill="both", expand=True)
        cols = ("date", "num", "buyer", "pln")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12, selectmode="browse")
        for cid, txt, w in [
            ("date", "Data", 95), ("num", "Numer", 120), ("buyer", "Nabywca", 220), ("pln", "PLN", 80),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        id_map: dict[str, str] = {}

        def refresh() -> None:
            id_map.clear()
            for i in tree.get_children():
                tree.delete(i)
            for row in list_importable_invoices(self._year):
                iid = tree.insert("", "end", values=(
                    row.get("issue_date", ""),
                    row.get("number", ""),
                    row.get("buyer", ""),
                    f"{row.get('amount_pln', 0):.2f}",
                ))
                id_map[iid] = row["id"]

        def import_one() -> None:
            sel = tree.selection()
            if not sel:
                return
            inv_id = id_map.get(sel[0], "")
            if not inv_id:
                return
            ok, msg = import_invoice(inv_id)
            if ok:
                show_toast(outer, msg)
                refresh()
            else:
                messagebox.showwarning("DNR", msg, parent=outer)

        def import_all() -> None:
            pending = list_importable_invoices(self._year)
            if not pending:
                messagebox.showinfo("DNR", "Brak faktur do importu.", parent=outer)
                return
            if not messagebox.askyesno(
                "DNR",
                f"Zaimportować {len(pending)} faktur(y) za {self._year}?",
                parent=outer,
            ):
                return
            imported, skipped, _errs = import_all_for_year(self._year)
            show_toast(outer, f"Zaimportowano {imported}, pominięto {skipped}.")
            refresh()

        btn_row = tk.Frame(inv_frame, bg=_BG)
        btn_row.pack(fill="x", pady=8)
        ttk.Button(btn_row, text="Odśwież faktury", command=refresh).pack(side="left")
        ttk.Button(btn_row, text="Importuj zaznaczoną", command=import_one).pack(side="left", padx=8)
        ttk.Button(btn_row, text=f"Importuj wszystkie faktury ({self._year})", command=import_all).pack(side="left", padx=8)

        shop_blocked, shop_block_msg = shopify_dnr_import_blocked()
        shop_frame = ttk.LabelFrame(
            body,
            text=" Shopify (opłacone zamówienia) " if not shop_blocked else " Shopify — wyłączony ",
            padding=8,
        )
        shop_frame.pack(fill="x")
        if shop_blocked:
            tk.Label(
                shop_frame,
                text=shop_block_msg,
                bg="#fff8e1",
                fg="#e65100",
                font=("Segoe UI", 9),
                wraplength=720,
                justify="left",
                padx=8,
                pady=8,
            ).pack(fill="x")
            tk.Label(
                shop_frame,
                text="Użyj importu faktur powyżej. Import Shopify pozostaje tylko gdy moduł faktur nie jest dostępny.",
                bg=_BG,
                fg="#666",
                font=("Segoe UI", 8),
                wraplength=720,
                justify="left",
            ).pack(anchor="w", pady=(0, 4))
        else:
            tk.Label(
                shop_frame,
                text="Import po opłaceniu — tryb awaryjny (brak modułu faktur).",
                bg=_BG, fg="#555", font=("Segoe UI", 9),
            ).pack(anchor="w")

            def import_shopify_all() -> None:
                pending = list_importable_shopify_orders(self._year)
                if not pending:
                    messagebox.showinfo("DNR", "Brak zamówień Shopify do importu.", parent=outer)
                    return
                if not messagebox.askyesno(
                    "DNR",
                    f"Zaimportować {len(pending)} zamówień Shopify za {self._year}?",
                    parent=outer,
                ):
                    return
                imported, skipped = import_all_shopify_for_year(self._year)
                show_toast(outer, f"Shopify: {imported} zaimportowano, {skipped} pominięto.")
                refresh()

            shop_row = tk.Frame(shop_frame, bg=_BG)
            shop_row.pack(fill="x", pady=6)
            shop_count = len(list_importable_shopify_orders(self._year))
            ttk.Button(
                shop_row,
                text=f"Importuj Shopify ({shop_count} do importu)",
                command=import_shopify_all,
            ).pack(side="left")
        refresh()
        self._swap(outer)

    def show_export(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Eksport", back=self._back_for("export"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=16)
        body.pack(fill="both", expand=True)

        year_var = tk.StringVar(value=str(self._year))
        row = tk.Frame(body, bg=_BG)
        row.pack(anchor="w")
        ttk.Label(row, text="Rok").pack(side="left")
        ttk.Entry(row, textvariable=year_var, width=6).pack(side="left", padx=4)
        path_lbl = tk.Label(body, text="", bg=_BG, fg="#333", font=("Segoe UI", 10), wraplength=600, justify="left")
        path_lbl.pack(anchor="w", pady=12)

        def do_export() -> None:
            try:
                y = int(year_var.get())
            except ValueError:
                messagebox.showerror("DNR", "Nieprawidłowy rok.", parent=outer)
                return
            self._year = y
            path = export_year_csv(y)
            path_lbl.config(text=f"Zapisano: {path}")
            show_toast(outer, "Wyeksportowano CSV.")

        def open_folder() -> None:
            text = path_lbl.cget("text")
            if not text.startswith("Zapisano:"):
                return
            folder = Path(text.replace("Zapisano:", "").strip()).parent
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)

        ttk.Button(body, text="Eksportuj CSV", command=do_export).pack(anchor="w")
        ttk.Button(body, text="Otwórz folder", command=open_folder).pack(anchor="w", pady=8)
        self._swap(outer)

    def show_month_close(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Zamknięcie miesiąca — DNR", back=self._back_for("month_close"))
        top = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        top.pack(fill="x")
        y_var = tk.IntVar(value=date.today().year)
        m_var = tk.IntVar(value=date.today().month)
        ttk.Label(top, text="Rok:").pack(side="left")
        ttk.Spinbox(top, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        ttk.Label(top, text="Miesiąc:").pack(side="left", padx=(8, 0))
        ttk.Spinbox(top, from_=1, to=12, textvariable=m_var, width=4).pack(side="left", padx=4)

        summary_var = tk.StringVar(value="")
        ttk.Label(
            outer,
            text="Checklista DNR — rachunki, wpisy w ewidencji, eksport. Bez zamknięcia KPiR.",
            foreground="#666",
            wraplength=720,
        ).pack(anchor="w", padx=16, pady=(0, 4))
        ttk.Label(outer, textvariable=summary_var, wraplength=720, justify="left").pack(
            anchor="w", padx=16, pady=(0, 4),
        )
        checklist_txt = tk.Text(outer, height=14, width=80, font=("Consolas", 9), wrap="word")
        checklist_txt.pack(fill="both", expand=True, padx=16, pady=8)

        def refresh() -> None:
            from .month_checklist import build_dnr_month_checklist

            cl = build_dnr_month_checklist(y_var.get(), m_var.get())
            summary_var.set(
                f"Ostrzeżenia: {cl.warning_count} · Błędy: {cl.blocking_count} · "
                f"{'OK do archiwizacji' if cl.can_close else 'Uzupełnij pozycje'}"
            )
            lines = []
            for item in cl.items:
                icon = {"error": "✗", "warning": "!", "info": "i"}.get(item.severity, "•")
                lines.append(f"  {icon} [{item.category}] {item.message}")
            if not lines:
                lines.append("  (brak problemów)")
            checklist_txt.configure(state="normal")
            checklist_txt.delete("1.0", "end")
            checklist_txt.insert("1.0", "\n".join(lines))
            checklist_txt.configure(state="disabled")

        def import_catchup() -> None:
            y = y_var.get()
            if not messagebox.askyesno(
                "Import DNR (zaległe)",
                f"Zaimportować wystawione rachunki z {y} bez wpisu DNR?",
                parent=outer,
            ):
                return
            imported, skipped, errors = import_all_for_year(y)
            show_toast(outer, f"DNR: zaimportowano {imported}", bg="#2e7d32")
            msg = f"Zaimportowano: {imported}\nPominięto: {skipped}"
            if errors:
                msg += "\n\n" + "\n".join(errors[:10])
            messagebox.showinfo("Import DNR", msg, parent=outer)
            refresh()

        def export_invoices() -> None:
            try:
                from Komponenty.dokumentysprzedazy.export_monthly import export_month_csv
                path = export_month_csv(y_var.get(), m_var.get())
                show_toast(outer, f"Eksport faktur: {path.name}", bg="#1565c0")
            except Exception as exc:
                messagebox.showerror("Eksport", str(exc), parent=outer)

        def export_dnr() -> None:
            try:
                path = export_year_csv(y_var.get())
                show_toast(outer, f"Eksport DNR: {path.name}", bg="#1565c0")
            except Exception as exc:
                messagebox.showerror("Eksport", str(exc), parent=outer)

        btns = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Import DNR (zaległe)", command=import_catchup).pack(side="left", padx=4)
        ttk.Button(btns, text="Eksport rachunków (CSV)", command=export_invoices).pack(side="left", padx=4)
        ttk.Button(btns, text="Eksport DNR (CSV)", command=export_dnr).pack(side="left", padx=4)
        refresh()
        self._swap(outer)

    def show_settings(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Ustawienia", back=self._back_for("settings"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=16)
        body.pack(fill="both", expand=True)

        settings = load_settings()
        owner_var = tk.StringVar(value=settings.owner_name)
        limit_var = tk.StringVar(value=str(settings.quarterly_limit))
        notes_var = tk.StringVar(value=settings.notes)
        elig_vars = {
            key: tk.BooleanVar(value=bool(settings.eligibility.get(key)))
            for key, _ in ELIGIBILITY_ITEMS
        }

        form = ttk.LabelFrame(body, text="DNR", padding=12)
        form.pack(fill="x")
        for row_i, (lbl, var) in enumerate([
            ("Nazwa / podmiot", owner_var),
            ("Limit kwartalny przychodu należnego (PLN)", limit_var),
            ("Notatki", notes_var),
        ]):
            ttk.Label(form, text=lbl).grid(row=row_i, column=0, sticky="w", pady=4, padx=(0, 8))
            width = 50 if lbl == "Notatki" else 20
            ttk.Entry(form, textvariable=var, width=width).grid(row=row_i, column=1, sticky="w", pady=4)
        ttk.Label(
            form,
            text=f"Domyślnie 2026: {DEFAULT_QUARTERLY_LIMIT:.2f} PLN ({TAX_CONFIG_ID}).",
            foreground="#666",
        ).grid(row=2, column=1, sticky="w", pady=(0, 4))

        elig_frame = ttk.LabelFrame(body, text=" Warunki DNR (checklista) ", padding=12)
        elig_frame.pack(fill="x", pady=(12, 0))
        for i, (key, label) in enumerate(ELIGIBILITY_ITEMS):
            ttk.Checkbutton(elig_frame, text=label, variable=elig_vars[key]).grid(
                row=i, column=0, sticky="w", pady=2,
            )

        def save() -> None:
            try:
                limit = float(str(limit_var.get()).replace(",", ".").replace(" ", ""))
            except ValueError:
                messagebox.showerror("DNR", "Nieprawidłowy limit.", parent=outer)
                return
            eligibility = {key: bool(elig_vars[key].get()) for key, _ in ELIGIBILITY_ITEMS}
            confirmed_at = ""
            if all(eligibility.values()):
                from datetime import datetime
                confirmed_at = datetime.now().isoformat(timespec="seconds")
            current = load_settings()
            save_canonical_quarterly_limit(limit)
            save_settings(DnrSettings(
                owner_name=owner_var.get().strip(),
                quarterly_limit=limit,
                notes=notes_var.get().strip(),
                eligibility=eligibility,
                eligibility_confirmed_at=confirmed_at or current.eligibility_confirmed_at,
                migration=current.migration,
            ))
            show_toast(outer, "Zapisano ustawienia.")

        ttk.Button(form, text="Zapisz", command=save).grid(row=4, column=1, sticky="w", pady=8)
        self._swap(outer)
