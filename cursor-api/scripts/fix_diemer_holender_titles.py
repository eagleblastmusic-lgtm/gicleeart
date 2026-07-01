"""Poprawka tytulow: Michael Zeno Diemer — Latajacy Holender (70x95 + 90x120)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.description_update import (
    apply_product_title_fields,
    load_product_title_fields,
    set_title_update_mark,
)

ARTIST = "Michael Zeno Diemer"

PRODUCTS = (
    {
        "product_id": 15611421098332,
        "label": "Holender 70x95",
        "titles": {
            "orig": "Der fliegende Holländer (70x95)",
            "pl": "Latający Holender (70x95)",
            "en": "The Flying Dutchman (70x95)",
            "de": "Der fliegende Holländer (70x95)",
            "fr": (
                "Le Vaisseau fantôme (70x95) "
                "(ou Le Hollandais volant (70x95))"
            ),
            "es": "El holandés errante (70x95)",
            "nl": "De Vliegende Hollander (70x95)",
            "it": "L'olandese volante (70x95)",
        },
    },
    {
        "product_id": 15611421655388,
        "label": "Holender 90x120",
        "titles": {
            "orig": "Der fliegende Holländer (90x120) (of Das Geisterschiff)",
            "pl": "Latający Holender (90x120) (lub Statek widmo)",
            "en": "The Flying Dutchman (90x120) (or The Ghost Ship)",
            "de": (
                "Der fliegende Holländer (90x120) "
                "(oder Das Geisterschiff)"
            ),
            "fr": (
                "Le Vaisseau fantôme (90x120) "
                "(ou Le Hollandais volant (90x120)/Le Navire fantôme)"
            ),
            "es": "El holandés errante (90x120) (o El buque fantasma)",
            "nl": "De Vliegende Hollander (90x120) (of Het spookschip)",
            "it": (
                "L'olandese volante (90x120) "
                "(o Il vascello fantasma)"
            ),
        },
    },
)


def main() -> int:
    for cfg in PRODUCTS:
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
    print(f"\nGotowe — {len(PRODUCTS)} produktow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
