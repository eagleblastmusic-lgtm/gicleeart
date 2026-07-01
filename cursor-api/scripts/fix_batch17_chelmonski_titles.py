"""Poprawka tytulow: batch 17 — Jozef Chelmonski (3)."""
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


ARTIST = "Józef Chełmoński"

PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611547189596,
        "artist": ARTIST,
        "label": "Babie lato",
        "titles": {
            "orig": "Babie lato",
            "pl": "Babie lato",
            "en": "Indian Summer",
            "de": "Altweibersommer",
            "fr": "Été de la Saint-Martin (ou L'été indien)",
            "es": "Veranillo de San Martín (o El verano de las viejas)",
            "nl": "Nazomer",
            "it": "Estate di San Martino",
        },
    },
    {
        "product_id": 15611547320668,
        "artist": ARTIST,
        "label": "Bociany",
        "titles": {
            "orig": "Bociany",
            "pl": "Bociany",
            "en": "Storks",
            "de": "Die Störche",
            "fr": "Les Cigognes",
            "es": "Las cigüeñas",
            "nl": "Ooievaars",
            "it": "Le cicogne",
        },
    },
    {
        "product_id": 15611547386204,
        "artist": ARTIST,
        "label": "Kurka wodna",
        "titles": {
            "orig": "Kurka wodna",
            "pl": "Kurka wodna",
            "en": "The Water Hen (or Common Moorhen)",
            "de": "Das Teichhuhn (oder Die Teichhenne)",
            "fr": "La Poule d'eau",
            "es": "La gallineta común (o Polla de agua)",
            "nl": "Het waterhoen (of Het waterhoentje)",
            "it": "La gallinella d'acqua",
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 17).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
