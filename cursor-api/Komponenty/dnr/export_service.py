"""Eksport ewidencji DNR do CSV."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .constants import DEFAULT_QUARTERLY_LIMIT, QUARTER_LABELS, SALE_KIND_LABELS, SOURCE_LABELS
from .storage import exports_dir, list_costs, list_sales
from .summary_service import pit_cash_revenue_for_year, quarterly_breakdown, year_limit_revenue


def export_year_csv(year: int) -> Path:
    out = exports_dir(year) / f"dnr_ewidencja_{year}.csv"
    sales = [s for s in list_sales() if s.event_date.startswith(f"{year:04d}")]
    costs = [c for c in list_costs() if c.event_date.startswith(f"{year:04d}")]
    sales.sort(key=lambda x: x.event_date)
    costs.sort(key=lambda x: x.event_date)

    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow([f"Ewidencja DNR — rok {year}"])
        w.writerow(["Limit kwartalny przychodu należnego (domyślnie)", f"{DEFAULT_QUARTERLY_LIMIT:.2f} PLN"])
        w.writerow([])
        w.writerow(["KWARTAŁY — limit przychodu należnego"])
        w.writerow(["Kwartał", "Przychód należny", "Limit", "Pozostało", "Przekroczono"])
        for row in quarterly_breakdown(year):
            w.writerow([
                QUARTER_LABELS[row["quarter"]],
                f"{row['limit_revenue']:.2f}",
                f"{row['quarterly_limit']:.2f}",
                f"{row['remaining']:.2f}",
                "TAK" if row["over_limit"] else "NIE",
            ])
        w.writerow([])
        w.writerow(["PRZYCHODY (sprzedaż, zwroty, korekty)"])
        w.writerow([
            "Data", "Rodzaj", "Cena", "Rabat", "Przychód należny", "Wpływ na limit",
            "Płatność", "Wpływ kasowy PIT", "Opis", "Dokument", "Źródło",
        ])
        from .summary_service import sale_limit_delta, sale_pit_cash_delta

        for s in sales:
            delta = sale_limit_delta(s)
            w.writerow([
                s.event_date,
                SALE_KIND_LABELS.get(s.entry_kind or "sale", s.entry_kind),
                f"{s.list_price_pln:.2f}" if s.list_price_pln else "",
                f"{s.discount_pln:.2f}" if s.discount_pln else "",
                f"{s.amount_pln:.2f}",
                f"{delta:+.2f}",
                s.payment_status or "paid",
                f"{sale_pit_cash_delta(s):+.2f}",
                s.description,
                s.document_number,
                SOURCE_LABELS.get(s.source, s.source),
            ])
        w.writerow([])
        w.writerow(["KOSZTY (nie wchodzą do limitu)"])
        w.writerow(["Data", "Kwota PLN", "Kategoria", "Opis", "Sprzedawca", "Dokument"])
        for c in costs:
            w.writerow([
                c.event_date,
                f"{c.amount_pln:.2f}",
                c.category,
                c.description,
                c.seller,
                c.document_number,
            ])
        rev = year_limit_revenue(year)
        cos = sum(c.amount_pln for c in costs)
        w.writerow([])
        w.writerow(["PODSUMOWANIE ROKU"])
        w.writerow(["Przychód należny (suma kwartałów)", f"{rev:.2f}"])
        w.writerow(["Wpływy kasowe PIT (rok)", f"{pit_cash_revenue_for_year(year):.2f}"])
        w.writerow(["Koszty", f"{cos:.2f}"])
        w.writerow(["Wynik", f"{rev - cos:.2f}"])
        w.writerow(["Wygenerowano", date.today().isoformat()])
    return out
