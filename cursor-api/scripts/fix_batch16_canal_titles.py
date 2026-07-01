"""Poprawka tytulow: batch 16 — Antonio Canal (5)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.description_update import (
    apply_product_title_fields,
    load_product_title_fields,
    set_title_update_mark,
)


class ProductTitles(TypedDict):
    product_id: int
    artist: str
    label: str
    titles: dict[str, str]


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15610497433948,
        "artist": "Antonio Canal",
        "label": "Regata Canal Grande",
        "titles": {
            "orig": "Regata sul Canal Grande (1982.32.2/B.M)",
            "pl": (
                "Regaty na Kanale Grande (1982.32.2/B.M) "
                "(lub Regata na Grand Canal (1982.32.2/B.M))"
            ),
            "en": (
                "A Regatta on the Grand Canal (1982.32.2/B.M) "
                "(or Regatta on the Grand Canal (1982.32.2/B.M))"
            ),
            "de": "Regatta auf dem Canal Grande (1982.32.2/B.M)",
            "fr": "Régate sur le Grand Canal (1982.32.2/B.M)",
            "es": "Regata en el Gran Canal (1982.32.2/B.M)",
            "nl": "Regatta op het Canal Grande (1982.32.2/B.M)",
            "it": "Regata sul Canal Grande (1982.32.2/B.M)",
        },
    },
    {
        "product_id": 15611045413212,
        "artist": "Antonio Canal",
        "label": "St Marks Basin",
        "titles": {
            "orig": "Il Bacino di San Marco verso est",
            "pl": (
                "Basen San Marco w Wenecji "
                "(lub Widok na Bacino di San Marco w kierunku wschodnim/"
                "Basen św. Marka w stronę wschodnią)"
            ),
            "en": (
                "The Bacino di San Marco, Venice, Looking East "
                "(or The Bacino di San Marco Looking East)"
            ),
            "de": "Das Bacino di San Marco mit Blick nach Osten",
            "fr": (
                "Le bassin de Saint-Marc vers l'est "
                "(ou Le Bassin de Saint-Marc, Venise, regardant vers l'est)"
            ),
            "es": "El Bacino de San Marcos mirando hacia el este",
            "nl": "Het San Marcobekken in oostelijke richting",
            "it": (
                "Il Bacino di San Marco verso est "
                "(o Il Bacino di San Marco guardando verso est)"
            ),
        },
    },
    {
        "product_id": 15611050983772,
        "artist": "Antonio Canal",
        "label": "Canal Grande Salute",
        "titles": {
            "orig": "Il Canal Grande e la chiesa di Santa Maria della Salute",
            "pl": (
                "Kanał Grande i kościół Santa Maria della Salute "
                "(lub Widok na Grand Canal i kościół Santa Maria della Salute/"
                "Wejście do Kanału Grande z kościołem Santa Maria della Salute)"
            ),
            "en": (
                "The Grand Canal and the Church of the Salute "
                "(or The Entrance to the Grand Canal, Venice)"
            ),
            "de": (
                "Der Canal Grande und die Kirche Santa Maria della Salute "
                "(oder Die Einfahrt in den Canal Grande mit Santa Maria della Salute)"
            ),
            "fr": (
                "Le Grand Canal et l'église de la Salute "
                "(ou L'Entrée du Grand Canal avec l'église Santa Maria della Salute)"
            ),
            "es": (
                "El Gran Canal y la iglesia de Santa Maria della Salute "
                "(o La entrada al Gran Canal con la iglesia de la Salute)"
            ),
            "nl": (
                "Het Canal Grande en de kerk van Santa Maria della Salute "
                "(of De ingang van het Canal Grande met de Salute-kerk)"
            ),
            "it": (
                "Il Canal Grande e la chiesa di Santa Maria della Salute "
                "(o L'ingresso al Canal Grande con la chiesa della Salute)"
            ),
        },
    },
    {
        "product_id": 15611065762140,
        "artist": "Antonio Canal",
        "label": "Riva Schiavoni 1951.404",
        "titles": {
            "orig": "Riva degli Schiavoni verso est (1951.404)",
            "pl": (
                "Riva degli Schiavoni w stronę wschodnią (1951.404) "
                "(lub Widok na Riva degli Schiavoni w Wenecji (1951.404))"
            ),
            "en": (
                "View of the Riva degli Schiavoni, Venice (1951.404) "
                "(or Riva degli Schiavoni looking East (1951.404))"
            ),
            "de": (
                "Riva degli Schiavoni gegen Osten (1951.404) "
                "(oder Blick auf die Riva degli Schiavoni, Venedig (1951.404))"
            ),
            "fr": (
                "La Riva degli Schiavoni vers l'est (1951.404) "
                "(ou Vue de la Riva degli Schiavoni, Venise (1951.404))"
            ),
            "es": (
                "Riva degli Schiavoni hacia el este (1951.404) "
                "(o Vista de la Riva degli Schiavoni, Venecia (1951.404))"
            ),
            "nl": (
                "Riva degli Schiavoni in oostelijke richting (1951.404) "
                "(of Gezicht op de Riva degli Schiavoni, Venetië (1951.404))"
            ),
            "it": (
                "Riva degli Schiavoni verso est (1951.404) "
                "(o Veduta della Riva degli Schiavoni verso est (1951.404))"
            ),
        },
    },
    {
        "product_id": 15611063042396,
        "artist": "Antonio Canal",
        "label": "Piazza Navona",
        "titles": {
            "orig": "Roma: la Piazza Navona",
            "pl": (
                "Rzym: Piazza Navona "
                "(lub Widok na Piazza Navona w Rzymie/Plac Navona w Rzymie)"
            ),
            "en": (
                "Rome: The Piazza Navona (or View of the Piazza Navona, Rome)"
            ),
            "de": (
                "Rom: Die Piazza Navona (oder Blick auf die Piazza Navona in Rom)"
            ),
            "fr": (
                "Rome : la place Navone (ou Vue de la place Navone, Rome)"
            ),
            "es": (
                "Roma: la Piazza Navona (o Vista de la Piazza Navona, Roma)"
            ),
            "nl": (
                "Rome: De Piazza Navona (of Gezicht op de Piazza Navona in Rome)"
            ),
            "it": (
                "Roma: la Piazza Navona (o Veduta di Piazza Navona, Roma)"
            ),
        },
    },
)


def _apply(cfg: ProductTitles) -> None:
    pid = cfg["product_id"]
    print(f"\n=== {cfg['label']} (id={pid}) ===")
    res = apply_product_title_fields(
        product_id=pid,
        artist=cfg["artist"],
        titles=cfg["titles"],
        logger=print,
    )
    set_title_update_mark(pid, marked=True)
    pl = load_product_title_fields(pid)
    print(f"  PL: {pl.get('pl', '')}")
    print(f"  locales: {res.get('saved_locales', [])}")


def main() -> int:
    for cfg in PRODUCTS:
        _apply(cfg)
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 16).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
