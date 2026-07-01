"""Poprawka tytulow: batch 18 — Thomas Cole (4)."""
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

ARTIST = "Thomas Cole"


class ProductTitles(TypedDict):
    product_id: int
    label: str
    titles: dict[str, str]


PRODUCTS: tuple[ProductTitles, ...] = (
    {
        "product_id": 15611243790684,
        "label": "Aniol pasterzom",
        "titles": {
            "orig": "The Angel Appearing to the Shepherds",
            "pl": (
                "Anioł objawiający się pasterzom "
                "(lub Anioł ukazujący się pasterzom)"
            ),
            "en": "The Angel Appearing to the Shepherds",
            "de": "Der Engel erscheint den Hirten",
            "fr": "L'Ange apparaissant aux bergers",
            "es": "El ángel apareciéndose a los pastores",
            "nl": "De engel verschijnt aan de herders",
            "it": "L'angelo che appare ai pastori",
        },
    },
    {
        "product_id": 15611247984988,
        "label": "Course of Empire Consummation",
        "titles": {
            "orig": "The Course of Empire: The Consummation of Empire",
            "pl": (
                "Dzieje imperium: zwieńczenie imperium "
                "(lub Zwieńczenie imperium/Dopełnienie z czasów Imperium)"
            ),
            "en": (
                "The Course of Empire: The Consummation of Empire "
                "(or The Consummation of Empire)"
            ),
            "de": (
                "Der Weg des Imperiums: Die Vollendung des Reichs "
                "(oder Die Vollendung des Reiches)"
            ),
            "fr": (
                "Le Cours de l'empire : Le Paroxysme de l'empire "
                "(ou Consommation de l'empire)"
            ),
            "es": "El curso del imperio: La consumación del imperio",
            "nl": (
                "De loop van het rijk: Het hoogtepunt van het rijk "
                "(of De voltooiing van het rijk)"
            ),
            "it": (
                "Il corso dell'impero: Il culmine dell'impero "
                "(o L'apoteosi dell'impero)"
            ),
        },
    },
    {
        "product_id": 15611247395164,
        "label": "Course of Empire Arcadian",
        "titles": {
            "orig": "The Course of Empire: The Arcadian or Pastoral State",
            "pl": (
                "Dzieje imperium: stan arkadyjski "
                "(lub sielski/Państwo pasterskie/Stan arkadyjski/sielski)"
            ),
            "en": (
                "The Course of Empire: The Arcadian or Pastoral State "
                "(or The Arcadian/Pastoral State)"
            ),
            "de": (
                "Der Weg des Imperiums: Der arkadische oder pastorale Zustand "
                "(oder Der arkadische Zustand)"
            ),
            "fr": (
                "Le Cours de l'empire : L'État arcadien ou pastoral "
                "(ou L'État pastoral)"
            ),
            "es": (
                "El curso del imperio: El estado arcádico o pastoral "
                "(o El estado pastoral)"
            ),
            "nl": (
                "De loop van het rijk: De Arcadische of pastorale staat "
                "(of De pastorale staat)"
            ),
            "it": (
                "Il corso dell'impero: Lo stato arcadico o pastorale "
                "(o Lo stato pastorale)"
            ),
        },
    },
    {
        "product_id": 15611247264092,
        "label": "Course of Empire Destruction",
        "titles": {
            "orig": "The Course of Empire: Destruction",
            "pl": (
                "Dzieje imperium: zagłada "
                "(lub Dzieje imperium: zniszczenie/Zagłada imperium)"
            ),
            "en": "The Course of Empire: Destruction (or Destruction)",
            "de": (
                "Der Weg des Imperiums: Destruction (oder Die Zerstörung)"
            ),
            "fr": "Le Cours de l'empire : La Destruction",
            "es": (
                "El curso del imperio: Destrucción (o La destrucción)"
            ),
            "nl": "De loop van het rijk: De verwoesting",
            "it": "Il corso dell'impero: La distruzione",
        },
    },
)


def _apply(cfg: ProductTitles) -> None:
    pid = cfg["product_id"]
    print(f"\n=== {cfg['label']} (id={pid}) ===")
    res = apply_product_title_fields(
        product_id=pid,
        artist=ARTIST,
        titles=cfg["titles"],
        logger=print,
    )
    set_title_update_mark(pid, marked=True)
    print(f"  PL: {load_product_title_fields(pid).get('pl', '')}")
    print(f"  locales: {res.get('saved_locales', [])}")


def main() -> int:
    for cfg in PRODUCTS:
        _apply(cfg)
    print(f"\nGotowe — {len(PRODUCTS)} produktow (batch 18).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
