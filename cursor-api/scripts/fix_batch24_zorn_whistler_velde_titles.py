"""Poprawka tytulow: batch 24 — Zorn (2), Whistler, Willem Velde."""
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
        "product_id": 15611292778844,
        "artist": "Anders Zorn",
        "label": "Taniec swietojanski",
        "titles": {
            "orig": "Midsommardans",
            "pl": (
                "Taniec świętojański "
                "(lub Taniec w noc świętojańską/Taniec przesilenia letniego)"
            ),
            "en": "Midsummer Dance",
            "de": "Mittsommertanz",
            "fr": "Danse de la Saint-Jean",
            "es": (
                "Baile de la noche de San Juan "
                "(o Danza de pleno verano)"
            ),
            "nl": "Midzomerdans",
            "it": "Danza di mezza estate",
        },
    },
    {
        "product_id": 15611292516700,
        "artist": "Anders Zorn",
        "label": "Po kapieli",
        "titles": {
            "orig": "Efter badet",
            "pl": "Po kąpieli",
            "en": "After the Bath",
            "de": "Nach dem Bad",
            "fr": "Après le bain",
            "es": "Después del baño",
            "nl": "Na het bad",
            "it": "Dopo il bagno",
        },
    },
    {
        "product_id": 15611526349148,
        "artist": "James Mcneill Whistler",
        "label": "Przy fortepianie",
        "titles": {
            "orig": "At the Piano",
            "pl": "Przy fortepianie",
            "en": "At the Piano",
            "de": "Am Klavier",
            "fr": "Au piano",
            "es": "Al piano",
            "nl": "Aan de piano",
            "it": "Al pianoforte",
        },
    },
    {
        "product_id": 15611428045148,
        "artist": "Willem Velde",
        "label": "Holenderskie okrety",
        "titles": {
            "orig": "Hollandse schepen op een kalme zee",
            "pl": (
                "Holenderskie okręty na spokojnym morzu "
                "(lub Cisza morska)"
            ),
            "en": (
                "Dutch Ships in a Calm "
                "(or Dutch Ships in a Calm Sea)"
            ),
            "de": (
                "Holländische Schiffe bei Windstille "
                "(oder Niederländische Schiffe auf ruhiger See)"
            ),
            "fr": "Navires hollandais par temps calme",
            "es": "Barcos holandeses en un mar en calma",
            "nl": "Hollandse schepen op een kalme zee",
            "it": "Navi olandesi in una marina calma",
        },
    },
)


def main() -> int:
    for cfg in PRODUCTS:
        pid = cfg["product_id"]
        print(f"\n=== {cfg['label']} (id={pid}) ===")
        res = apply_product_title_fields(
            product_id=pid,
            artist=cfg["artist"],
            titles=cfg["titles"],
            logger=print,
        )
        set_title_update_mark(pid, marked=True)
        print(f"  PL: {load_product_title_fields(pid).get('pl', '')}")
        print(f"  locales: {res.get('saved_locales', [])}")
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 24).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
