"""Przygotowanie danych do etykiet wysylkowych.

Dlaczego nie ma pelnej integracji API:
- **Furgonetka.pl** ma API ale wymaga umowy B2B z osobnym kluczem API
  (rejestracja jako przewoznik/nadawca firmowy).
- **Przesylarka.pl** nie wystawia publicznego API - to platforma webowa.
- **InPost Shipx** ma API dla nadawcow z umowa biznesowa (nie dla osob fizycznych).

Realistyczne podejscie dla sklepu e-commerce sprzedajacego kilka-
kilkanascie paczek dziennie: prefilled-form-redirect pattern.

Flow:
1. User klika 'Przygotuj przesylke -> Furgonetka.pl' (PL) albo
   'Przygotuj przesylke -> Przesylarka.pl' (zagranica).
2. Apka kopiuje dane odbiorcy + wymiary paczki do schowka w czytelnym
   formacie (imie, nazwisko, telefon, email, adres - kazde w osobnej linii).
3. Apka otwiera strone kuriera w przegladarce (https://furgonetka.pl/
   lub https://przesylarka.pl/).
4. User wkleja dane w panelu kuriera (Ctrl+V), wybiera kuriera i platnosc.
5. Po generowaniu etykiety (PDF) zapisuje numer trackingu w polu
   `tracking_number` w zamowienia.json (opcjonalne).

Detekcja kraju: jesli adres_wysylki zawiera 'Polska' albo 'Poland' lub
kod pocztowy w formacie NN-NNN -> Furgonetka. Inaczej -> Przesylarka.
"""

from __future__ import annotations

import re
from typing import Any

from Komponenty.produkcja.frame_variant import migrate_order_frame_fields, shipping_lookup_key
from Komponenty.produkcja import package_templates

# PL post code: 12-345
_PL_POSTCODE_RE = re.compile(r"\b\d{2}-\d{3}\b")
_PL_WORDS = ("polska", "poland", "pl,", " pl\n", " pl ")

_FURGONETKA_URL = "https://furgonetka.pl/"
_PRZESYLARKA_URL = "https://przesylarka.pl/"


def is_poland(address: str) -> bool:
    """Heurystyka: czy adres jest w Polsce."""
    a = (address or "").lower()
    if _PL_POSTCODE_RE.search(a):
        return True
    return any(w in a for w in _PL_WORDS)


def pick_carrier_url(order: dict) -> tuple[str, str]:
    """Zwraca (url, nazwa_kuriera) na podstawie adresu zamowienia."""
    if is_poland(order.get("adres_wysylki") or ""):
        return (_FURGONETKA_URL, "Furgonetka.pl")
    return (_PRZESYLARKA_URL, "Przesylarka.pl")


def format_clipboard_data(order: dict) -> str:
    """Formatuje dane odbiorcy + paczki jako tekst do wklejenia w formularzu kuriera."""
    migrate_order_frame_fields(order)
    lines: list[str] = []
    lines.append(f"=== {order.get('id', '')} ===")
    lines.append("")
    lines.append("ODBIORCA:")
    lines.append(order.get("client") or "(brak imienia i nazwiska)")
    adres = (order.get("adres_wysylki") or "").strip()
    if adres:
        for line in adres.split("\n"):
            if line.strip():
                lines.append(line.strip())
    lines.append("")
    lines.append("PRZEDMIOT:")
    lines.append(f"Reprodukcja: {order.get('tytul_obrazu') or '(brak tytulu)'}")
    lines.append(
        f"Ramka — drewno: {order.get('ramka_drewno', '')}  |  "
        f"rozmiar: {order.get('ramka_rozmiar', '')}  |  kolor: {order.get('ramka_kolor', '')}"
    )
    pp = (order.get("passepartout_kolor") or "").strip()
    if pp:
        lines.append(f"Passepartout: {pp}")
    lines.append(f"   (etykieta laczona: {order.get('ramka_wariant', '')})")
    lines.append(f"Ilosc: {order.get('ilosc', 1)}")
    lines.append("")
    lines.append("WYMIARY PACZKI (wpisz recznie - zaleznie od wariantu):")
    lookup_key = shipping_lookup_key(order)
    suggested = _suggested_dimensions(lookup_key)
    if suggested:
        lines.append(f"  {suggested}")
    else:
        lines.append("  Dlugosc: __ cm")
        lines.append("  Szerokosc: __ cm")
        lines.append("  Wysokosc: __ cm")
        lines.append("  Waga: __ kg")
    lines.append("")
    lines.append("NUMER ZAMOWIENIA SHOPIFY:")
    lines.append(order.get("shopify_order_no") or "(brak)")
    return "\n".join(lines)


def _suggested_dimensions(variant: str) -> str:
    """Zwraca proponowane wymiary paczki dla danego wariantu ramki.

    Teraz czerpie z edytowalnej tabeli szablonow (`package_templates.json`).
    Jesli klucza nie ma w tabeli — zwraca pusty string (UI wpisze pola puste
    do uzupelnienia).
    """
    return package_templates.formatted_for_key(variant)
