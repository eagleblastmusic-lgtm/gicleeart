"""Jednorazowo: utworz / odswiez artyste «Butti, Lorenzo» (kolekcja + opis + menu + produkt)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.create import create_artist_collection_and_menu  # noqa: E402

TITLE = "Butti, Lorenzo"
LIFESPAN = "28 Sie 1805 – 15 Sie 1860"
PRODUCT_ID = 15611419165020
DESCRIPTION = """\
Lorenzo Valentino Butti był włoskim malarzem marynistą związanym z Triestem. Kształcił się w Wenecji i Mediolanie, a po latach pracy nad pejzażem i architekturą całkowicie poświęcił się scenom morskim, przedstawiając zarówno spokojne wybrzeża, jak i dramatyczne sztormy.

W jego obrazach szczególnie ważne były światło, ruch fal i atmosfera nadmorskiego pejzażu, dzięki czemu łączył akademicką precyzję z romantycznym nastrojem. Dziś Butti jest kojarzony przede wszystkim z XIX-wiecznym malarstwem morskim."""


def main() -> int:
    def log(msg: str) -> None:
        print(msg)

    res = create_artist_collection_and_menu(
        collection_title=TITLE,
        product_ids=[PRODUCT_ID],
        description=DESCRIPTION,
        lifespan=LIFESPAN,
        portrait_path=None,
        logger=log,
    )
    print("\n=== Wynik ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
    if res.get("menu_error"):
        return 2
    if res.get("enrich_error"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
