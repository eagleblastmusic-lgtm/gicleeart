"""Jednorazowo: utworz / odswiez artyste «Chelius, Adolf» (kolekcja + opis + menu, bez portretu)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.create import create_artist_collection_and_menu  # noqa: E402

TITLE = "Chelius, Adolf"
LIFESPAN = "30 Maj 1856 – 28 Sty 1923"
DESCRIPTION = """\
Adolf Chelius był niemieckim malarzem pejzaży i scen rodzajowych z końca XIX i początku XX wieku. Urodzony we Frankfurcie nad Menem, studiował w akademiach sztuk pięknych w Berlinie i Wiedniu, a warsztat kształtował m.in. w Städelskim Instytucie Sztuki oraz w kolonii malarskiej w Kronbergu.

Od 1882 roku mieszkał w Monachium, skąd w latach 1885–1895 odbywał długie podróże studyjne po Europie — od Skandynawii po Włochy i Hiszpanię. W swoich obrazach łączył wrażliwość obserwatora natury z klasyczną kompozycją pejzażu; szczególnie dobrze oddawał światło, fakturę drzew i spokojną atmosferę wiejskich alei oraz pastwisk.

Chelius tworzył w nurcie realizmu i malarstwa plenerowego. Jego prace, choć dziś mniej znane niż u czołowych modernistów epoki, zachwycają harmonią koloru i czułością wobec codziennego krajobrazu Bawarii i innych regionów Europy."""

def main() -> int:
    def log(msg: str) -> None:
        print(msg)

    res = create_artist_collection_and_menu(
        collection_title=TITLE,
        product_ids=[],
        description=DESCRIPTION,
        lifespan=LIFESPAN,
        portrait_path=None,
        logger=log,
    )
    print("\n=== Wynik ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
    return 0 if not res.get("enrich_error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
