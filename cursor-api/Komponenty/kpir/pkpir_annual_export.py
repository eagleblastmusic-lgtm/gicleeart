"""Eksport roczny PKPiR — struktura logiczna (Dz.U. 2025 poz. 1299)."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .annual_income import annual_income_breakdown
from .entry_service import filter_entries
from .official_columns import COLUMN_KEYS, entry_to_official_row, monthly_cumulative_rows, sum_official_columns
from .official_export import export_official_pkpir_csv, export_official_pkpir_pdf, export_official_pkpir_xlsx
from .storage import documents_dir_for, load_settings


def _el(parent: ET.Element, tag: str, text: str | float | int = "") -> ET.Element:
    node = ET.SubElement(parent, tag)
    if text != "":
        node.text = str(text)
    return node


def _official_rows_for_year(year: int) -> list[dict[str, Any]]:
    settings = load_settings()
    entries = [
        e for e in filter_entries(year=year)
        if e.status in ("posted", "corrected")
    ]
    entries.sort(key=lambda x: (x.event_date, x.entry_number))
    return [entry_to_official_row(i, e, settings=settings) for i, e in enumerate(entries, 1)]


def export_pkpir_annual_xml(year: int) -> Path:
    """Roczny XML PKPiR — wariant zgodny ze strukturą JPK_PKPIR (do wysyłki / archiwum)."""
    settings = load_settings()
    rows = _official_rows_for_year(year)
    totals = sum_official_columns(rows)
    income = annual_income_breakdown(year, settings)

    root = ET.Element("JPK")
    _el(root, "KodFormularza", "JPK_PKPIR")
    _el(root, "WariantFormularza", "7")
    _el(root, "CelZlozenia", "1")
    _el(root, "RokDataOd", f"{year}-01-01")
    _el(root, "RokDataDo", f"{year}-12-31")
    _el(root, "DataWytworzeniaJPK", datetime.now().isoformat(timespec="seconds"))

    podmiot = ET.SubElement(root, "Podmiot1")
    _el(podmiot, "NIP", settings.seller_nip or "")
    _el(podmiot, "PelnaNazwa", settings.seller_name or "")
    _el(podmiot, "Adres", settings.seller_address or "")
    _el(podmiot, "RodzajDzialalnosci", settings.activity_description or "")

    pkpir = ET.SubElement(root, "PKPIR")
    for row in rows:
        w = ET.SubElement(pkpir, "Wiersz")
        for key in COLUMN_KEYS:
            val = row.get(key, "")
            tag = key[0].upper() + key[1:]
            if isinstance(val, float):
                _el(w, tag, f"{val:.2f}")
            else:
                _el(w, tag, val)

    podsum = ET.SubElement(root, "PodsumowanieRoczne")
    for key in (
        "revenue_goods", "revenue_other", "total_revenue",
        "purchase_goods", "purchase_side", "wages", "other_expenses", "total_expenses",
    ):
        _el(podsum, key, f"{totals.get(key, 0):.2f}")
    _el(podsum, "RemanentPoczatkowy", f"{income['inventory_opening']:.2f}")
    _el(podsum, "RemanentKoncowy", f"{income['inventory_closing']:.2f}")
    _el(podsum, "Dochod", f"{income['income']:.2f}")

    out_dir = documents_dir_for("exports", year, 12)
    out = out_dir / f"pkpir_roczny_{year:04d}.xml"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return out


def export_pkpir_annual_package(year: int) -> Path:
    """Pełny pakiet roczny: CSV/XLSX/PDF 19 kolumn + XML + README + instrukcja."""
    base = documents_dir_for("exports", year, 12)
    pkg = base / f"pkpir_roczny_{year:04d}"
    pkg.mkdir(parents=True, exist_ok=True)

    paths = [
        export_official_pkpir_csv(year),
        export_pkpir_annual_xml(year),
    ]
    try:
        paths.append(export_official_pkpir_xlsx(year))
    except ImportError:
        pass
    try:
        paths.append(export_official_pkpir_pdf(year))
    except ImportError:
        pass

    for src in paths:
        if src.is_file():
            shutil.copy2(src, pkg / src.name)

    instruction = pkg / "INSTRUKCJA_OBSLUGI_PKPIR.txt"
    instruction.write_text(
        "INSTRUKCJA OBSŁUGI PROGRAMU — Podatkowa Księga Przychodów i Rozchodów\n"
        "Moduł: GicleeApp / Komponenty/kpir\n"
        f"Rok podatkowy: {year}\n\n"
        "1. Przychody księgowane wyłącznie z wystawionych faktur.\n"
        "2. Koszty — z załącznikiem PDF lub importu bankowego; data wg metody memoriałowej/kasowej.\n"
        "3. Remanent — obowiązkowy na 1 I i 31 XII; wycena w 14 dni.\n"
        "4. Eksport roczny XML — przekaż do US do 30 kwietnia (forma elektroniczna od 2026).\n"
        "5. Kopia zapasowa: folder documents/ oraz kpir.json.\n",
        encoding="utf-8",
    )

    readme = pkg / "README.txt"
    readme.write_text(
        f"Pakiet roczny PKPiR — {year}\n"
        f"Wygenerowano: {date.today().isoformat()}\n"
        f"Pliki: {', '.join(p.name for p in pkg.iterdir() if p.is_file())}\n",
        encoding="utf-8",
    )
    return pkg


def annual_export_metadata(year: int) -> dict[str, Any]:
    rows = _official_rows_for_year(year)
    return {
        "year": year,
        "row_count": len(rows),
        "monthly_cumulative_dec": monthly_cumulative_rows(rows, through_month=12),
        "format": "PKPiR roczny — 19 kolumn + XML (Dz.U. 2025 poz. 1299)",
    }
