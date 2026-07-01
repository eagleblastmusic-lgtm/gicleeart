"""Eksport JPK_PKPIR — XML uproszczony."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

from .entry_service import filter_entries
from .official_columns import entry_to_official_row
from .storage import documents_dir_for, load_settings


def _el(parent: ET.Element, tag: str, text: str | float | int = "") -> ET.Element:
    node = ET.SubElement(parent, tag)
    if text != "":
        node.text = str(text)
    return node


def export_jpk_pkpir_xml(year: int, month: int) -> Path:
    """Generuje XML JPK_PKPIR (19 kolumn) — miesięczny."""
    settings = load_settings()
    entries = [
        e for e in filter_entries(year=year, month=month)
        if e.status in ("posted", "corrected")
    ]
    entries.sort(key=lambda x: (x.event_date, x.entry_number))

    root = ET.Element("JPK")
    _el(root, "KodFormularza", "JPK_PKPIR")
    _el(root, "WariantFormularza", "7")
    _el(root, "CelZlozenia", "1")
    _el(root, "DataWytworzeniaJPK", date.today().isoformat())
    _el(root, "DataOd", f"{year:04d}-{month:02d}-01")
    last_day = 28 if month == 2 else (30 if month in (4, 6, 9, 11) else 31)
    _el(root, "DataDo", f"{year:04d}-{month:02d}-{last_day:02d}")

    podmiot = ET.SubElement(root, "Podmiot1")
    _el(podmiot, "NIP", settings.seller_nip or "0000000000")
    _el(podmiot, "PelnaNazwa", settings.seller_name or "Podmiot")

    pkpir = ET.SubElement(root, "PKPIR")
    for i, e in enumerate(entries, 1):
        row = entry_to_official_row(i, e, settings=settings)
        w = ET.SubElement(pkpir, "Wiersz")
        _el(w, "Lp", row["lp"])
        _el(w, "DataZdarzenia", row["event_date"])
        _el(w, "NrKSeF", row["ksef_number"])
        _el(w, "NrDowodu", row["document_number"])
        _el(w, "NIPKontrahenta", row["contractor_nip"])
        _el(w, "Kontrahent", row["contractor"])
        _el(w, "AdresKontrahenta", row["contractor_address"])
        _el(w, "OpisZdarzenia", row["description"])
        _el(w, "PrzychodTowary", f"{row['revenue_goods']:.2f}")
        _el(w, "PrzychodPozostale", f"{row['revenue_other']:.2f}")
        _el(w, "PrzychodRazem", f"{row['total_revenue']:.2f}")
        _el(w, "ZakupTowary", f"{row['purchase_goods']:.2f}")
        _el(w, "KosztyUboczne", f"{row['purchase_side']:.2f}")
        _el(w, "Wynagrodzenia", f"{row['wages']:.2f}")
        _el(w, "PozostaleWydatki", f"{row['other_expenses']:.2f}")
        _el(w, "WydatkiRazem", f"{row['total_expenses']:.2f}")
        _el(w, "KolumnaWolna", row["other_events"])
        _el(w, "KosztyBR", f"{row['rd_expenses']:.2f}")
        _el(w, "Uwagi", row["notes"])

    out_dir = documents_dir_for("exports", year, month)
    out = out_dir / f"jpk_pkpir_{year:04d}_{month:02d}.xml"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out


def jpk_metadata(year: int, month: int) -> dict[str, Any]:
    entries = filter_entries(year=year, month=month, status="posted")
    return {
        "year": year,
        "month": month,
        "row_count": len(entries),
        "format": "JPK_PKPIR wariant 7 (19 kolumn, Dz.U. 2025 poz. 1299)",
    }
