"""Jednorazowo: utworz artyste «Ter Borch, Gesina» (kolekcja + opis + portret + menu)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Komponenty.dodajobraz.create import create_artist_collection_and_menu  # noqa: E402

TITLE = "Ter Borch, Gesina"
LIFESPAN = "15 Lis 1631 – 16 Kwi 1690"
DESCRIPTION = """\
Gesina ter Borch była holenderską artystką epoki złotej, tworzącą głównie akwarele i rysunki. Siostra sławnego Gerarda ter Borcha dorastała w domu pełnym obrazów i rozmów o sztuce, a własną drogę wytyczyła sobie w dziedzinie delikatnego rysunku i akwareli — w codziennych, intymnych scenach z życia XVII-wiecznej Holandii.

Jej prace charakteryzują się precyzyjną obserwacją, subtelną grą światła i ciepłą atmosferą. Gesina dokumentowała dom, rodzinę i zwyczajne chwile, łącząc warsztatowe rzemiosło z wrażliwością opowiadaczki obrazów. Choć przez długi czas pozostawała w cieniu bardziej znanych malarzy, dziś uznawana jest za jedną z ważniejszych artystek holenderskich swojej epoki."""

PORTRAIT = ROOT / "Komponenty" / "dodajobraz" / "data" / "Gesina_ter_Borch_portrait.png"


def main() -> int:
    if not PORTRAIT.is_file():
        print(f"Brak portretu: {PORTRAIT}")
        return 1

    def log(msg: str) -> None:
        print(msg)

    res = create_artist_collection_and_menu(
        collection_title=TITLE,
        product_ids=[],
        description=DESCRIPTION,
        lifespan=LIFESPAN,
        portrait_path=PORTRAIT,
        logger=log,
    )
    print("\n=== Wynik ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
    return 0 if not res.get("enrich_error") else 2


if __name__ == "__main__":
    raise SystemExit(main())
